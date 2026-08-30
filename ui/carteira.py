"""
Aba "📈 Carteira" — cards de resumo, tabela detalhada de posições (com
Preço Teto/Margem/Indicação) + empresas-alvo, e o gráfico de alocação
(por ativo ou por setor), igual ao dashboard original.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from core import calculations as calc
from core import rebalanceamento as rebal
from core.config import SETORES_PADRAO
from core.formatting import formatar_moeda_priv, formatar_pct, mascarar_qtd
from ui.acoes_comuns import atualizar_dados, exibir_status_cotacoes
from ui.ativos import montar_lista_ativos
from ui.styles import badge_alerta, badge_html, badge_indicacao, badge_variacao_dia, card_kpi_html, render_cards

PALETA_ALOCACAO = ["#34d399", "#38bdf8", "#fbbf24", "#a78bfa", "#fb7185", "#22d3ee", "#f472b6", "#a3e635", "#fb923c", "#94a3b8"]


def _grafico_alocacao(labels: list[str], valores: list[float]) -> go.Figure:
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=valores, hole=0.55,
        marker=dict(colors=PALETA_ALOCACAO, line=dict(color="#111827", width=2)),
        textinfo="percent", textfont=dict(color="#e5e7eb", size=12),
    )])
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(color="#9ca3af", size=11)),
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
    )
    return fig


def render(dados: dict, ocultar_valores: bool, salvar) -> None:
    st.title("Carteira Consolidada")
    st.caption("Posição por ativo, com preço médio, preço teto e alertas")

    col_titulo, col_botao = st.columns([3, 1])
    with col_botao:
        if st.button("🔄 Atualizar Cotações", use_container_width=True, type="primary"):
            atualizar_dados(dados, salvar)
            st.rerun()

    exibir_status_cotacoes()

    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    totais = calc.totais_carteira(posicoes)

    cor_lucro = "#34d399" if totais["lucro"] >= 0 else "#fb7185"
    cor_variacao = "#34d399" if totais["variacao_dia_reais"] >= 0 else "#fb7185"
    sinal_lucro = "+" if totais["lucro"] >= 0 else ""
    sinal_var = "+" if totais["variacao_dia_reais"] >= 0 else ""

    render_cards([
        card_kpi_html(
            "Patrimônio Atual", formatar_moeda_priv(totais["total_atual"], ocultar_valores),
            subvalor=f"{sinal_var}{formatar_moeda_priv(totais['variacao_dia_reais'], ocultar_valores)} no dia" if posicoes else None,
            cor_sub=cor_variacao,
        ),
        card_kpi_html("Total Investido", formatar_moeda_priv(totais["total_investido"], ocultar_valores), cor_valor="#d1d5db"),
        card_kpi_html("Lucro / Prejuízo Total", f"{sinal_lucro}{formatar_moeda_priv(totais['lucro'], ocultar_valores)}", cor_valor=cor_lucro),
        card_kpi_html("Rentabilidade Geral", f"{sinal_lucro}{formatar_pct(totais['rentabilidade_pct'])}", cor_valor=cor_lucro),
    ])

    col_tabela, col_grafico = st.columns([2, 1])

    with col_tabela:
        st.subheader("📌 Suas Posições")
        with st.form("form_empresa_alvo", clear_on_submit=True, border=False):
            c1, c2 = st.columns([3, 1])
            ticker_alvo = c1.text_input("Adicionar empresa alvo", placeholder="Ex: ITUB4", label_visibility="collapsed").strip().upper()
            enviado = c2.form_submit_button("🎯 Adicionar", use_container_width=True)
            if enviado and ticker_alvo:
                tickers_carteira = {p["ticker"] for p in posicoes}
                if ticker_alvo in tickers_carteira:
                    st.warning(f"{ticker_alvo} já é uma posição na sua carteira.")
                elif ticker_alvo in dados["watchlist"]:
                    st.info(f"{ticker_alvo} já está na lista de observação.")
                else:
                    dados["watchlist"].append(ticker_alvo)
                    salvar(dados)
                    st.rerun()

        lista_ativos = montar_lista_ativos(dados)
        if not lista_ativos:
            st.info('Nenhuma posição ainda. Vá até a aba "🧾 Compras & Vendas" e registre sua primeira compra.')
        else:
            lista_ordenada = _ordenar_lista_ativos(lista_ativos)
            _tabela_posicoes_html(lista_ordenada, ocultar_valores)
            _lista_remover_ativo(lista_ativos, dados, salvar)

    with col_grafico:
        st.subheader("Alocação")
        agrupar_por = st.radio("Agrupar por", ["Ativo", "Setor"], horizontal=True, label_visibility="collapsed")
        posicoes_com_valor = [p for p in posicoes if p["atual"] > 0]
        if not posicoes_com_valor:
            st.caption("Sem posições para exibir no gráfico ainda.")
        elif agrupar_por == "Ativo":
            fig = _grafico_alocacao([p["ticker"] for p in posicoes_com_valor], [p["atual"] for p in posicoes_com_valor])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            por_setor: dict[str, float] = {}
            for p in posicoes_com_valor:
                setor = dados["setores"].get(p["ticker"], "Sem setor definido")
                por_setor[setor] = por_setor.get(setor, 0) + p["atual"]
            fig = _grafico_alocacao(list(por_setor.keys()), list(por_setor.values()))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("⚙️ Definir setor de um ativo"):
        tickers_disponiveis = [p["ticker"] for p in posicoes]
        if tickers_disponiveis:
            c1, c2, c3 = st.columns([1, 1, 1])
            ticker_setor = c1.selectbox("Ativo", tickers_disponiveis, key="sel_ticker_setor")
            setor_escolhido = c2.selectbox(
                "Setor", SETORES_PADRAO,
                index=SETORES_PADRAO.index(dados["setores"][ticker_setor]) if dados["setores"].get(ticker_setor) in SETORES_PADRAO else 0,
                key="sel_setor",
            )
            if c3.button("Salvar setor", use_container_width=True):
                dados["setores"][ticker_setor] = setor_escolhido
                salvar(dados)
                st.rerun()
        else:
            st.caption("Registre uma compra primeiro para poder classificar por setor.")

    _secao_rebalanceamento(dados, ocultar_valores, posicoes, salvar)


def _secao_rebalanceamento(dados: dict, ocultar_valores: bool, posicoes: list[dict], salvar) -> None:
    st.subheader("🎯 Metas de Alocação & Rebalanceamento")
    st.caption(
        "Defina o % da carteira que cada ativo DEVERIA ter. Quando a cotação se mexe, o peso real se "
        "afasta da meta — aqui você vê o desvio e quanto compraria/venderia (em R$) para voltar ao alvo. "
        "Ativos sem meta definida não entram nesta conta."
    )

    tickers_disponiveis = sorted({p["ticker"] for p in posicoes if p["atual"] > 0})
    if not tickers_disponiveis:
        st.info("Registre ao menos uma compra para poder definir metas de alocação.")
        return

    metas_salvas = dados.get("metasAlocacao", {})

    with st.expander("⚙️ Definir metas (%)", expanded=not metas_salvas):
        with st.form("form_metas_alocacao"):
            novas_metas = {
                ticker: st.number_input(
                    ticker, min_value=0.0, max_value=100.0, value=float(metas_salvas.get(ticker, 0.0)), step=1.0,
                    key=f"meta_alocacao_{ticker}",
                )
                for ticker in tickers_disponiveis
            }
            soma = rebal.soma_metas_pct(novas_metas)
            aviso_soma = " ⚠️ passa de 100% — tudo bem se for de propósito, mas confira" if soma > 100 else ""
            st.caption(f"Soma das metas definidas: {soma:.1f}%{aviso_soma}")
            if st.form_submit_button("Salvar metas", type="primary", use_container_width=True):
                dados["metasAlocacao"] = {ticker: pct for ticker, pct in novas_metas.items() if pct > 0}
                salvar(dados)
                st.rerun()

    metas_ativas = {t: v for t, v in dados.get("metasAlocacao", {}).items() if v > 0}
    if not metas_ativas:
        st.caption("Nenhuma meta definida ainda.")
        return

    desvios = rebal.calcular_desvios(posicoes, metas_ativas)
    if not desvios:
        return

    linhas = []
    for d in desvios:
        cor = "#34d399" if d.desvio_pp >= 0 else "#fb7185"
        sinal = "+" if d.desvio_pp >= 0 else ""
        badge = badge_html("⚠️ Rebalancear", "warn") if d.alerta else badge_html("Dentro da meta", "ok")
        acao = "Vender" if d.valor_ajuste < 0 else "Comprar"
        linhas.append(
            f'<tr><td><span class="ticker">{d.ticker}</span></td>'
            f'<td>{formatar_pct(d.meta_pct)}</td><td>{formatar_pct(d.atual_pct)}</td>'
            f'<td><span style="color:{cor};font-weight:600">{sinal}{d.desvio_pp:.1f} p.p.</span></td>'
            f'<td>{acao} {formatar_moeda_priv(abs(d.valor_ajuste), ocultar_valores)}</td>'
            f'<td>{badge}</td></tr>'
        )
    colunas = ["Ativo", "Meta", "Atual", "Desvio", "Sugestão", "Status"]
    tabela_html = f"""
    <div style="overflow-x:auto">
    <table class="tabela-carteira">
        <thead><tr>{''.join(f'<th>{c}</th>' for c in colunas)}</tr></thead>
        <tbody>{''.join(linhas)}</tbody>
    </table>
    </div>
    """
    st.markdown(tabela_html, unsafe_allow_html=True)


# Cada opção do "Ordenar por": (rótulo, campo em cada dict de ui.ativos.montar_lista_ativos, decrescente_por_padrao)
CRITERIOS_ORDENACAO = [
    ("Ticker (A-Z)", "ticker", False),
    ("Total Atual", "atual", True),
    ("Resultado (R$)", "lucro_reais", True),
    ("Resultado (%)", "lucro_pct", True),
    ("Quantidade", "qtd_total", True),
    ("Preço Médio", "preco_medio_ponderado", True),
    ("Cotação Atual", "cotacao_atual", True),
    ("Variação do Dia (%)", "variacao_dia_pct", True),
    ("Preço Teto", "preco_teto", True),
    ("Margem vs Preço Médio (%)", "margem_vs_preco_medio", True),
]


def _ordenar_lista_ativos(lista_ativos: list[dict]) -> list[dict]:
    """
    Controles "Ordenar por" + crescente/decrescente acima da tabela de
    posições — clicar em cabeçalho de coluna não é possível na tabela em
    HTML (que existe pra poder colorir resultado, destacar empresa-alvo
    etc., algo que a tabela nativa do Streamlit não permite célula a
    célula), então a ordenação fica nestes dois controles em vez de nos
    cabeçalhos. Ativos sem valor no campo escolhido (ex: empresas-alvo, que
    não têm "Resultado") sempre ficam por último, em qualquer direção.
    """
    rotulos = [c[0] for c in CRITERIOS_ORDENACAO]
    col_criterio, col_direcao = st.columns([3, 2])
    with col_criterio:
        rotulo_escolhido = st.selectbox("↕️ Ordenar por", rotulos)
    campo, decrescente_padrao = next((c[1], c[2]) for c in CRITERIOS_ORDENACAO if c[0] == rotulo_escolhido)
    with col_direcao:
        decrescente = st.toggle("Decrescente", value=decrescente_padrao, key=f"toggle_ordenacao_{campo}")
        st.caption("🔽 Maior/Z primeiro" if decrescente else "🔼 Menor/A primeiro")

    return _aplicar_ordenacao(lista_ativos, campo, decrescente)


def _aplicar_ordenacao(lista_ativos: list[dict], campo: str, decrescente: bool) -> list[dict]:
    """
    Parte "pura" da ordenação (sem nenhuma chamada ao Streamlit), separada
    só para poder ser testada isoladamente. Ativos sem valor no campo
    escolhido (ex: empresas-alvo sem "Resultado") sempre ficam por último,
    não importa a direção escolhida.
    """
    com_valor = [a for a in lista_ativos if a.get(campo) is not None]
    sem_valor = [a for a in lista_ativos if a.get(campo) is None]
    com_valor.sort(key=lambda a: a[campo], reverse=decrescente)
    return com_valor + sem_valor


def _tabela_posicoes_html(lista_ativos: list[dict], ocultar_valores: bool) -> None:
    linhas = []
    for a in lista_ativos:
        classe_linha = ' class="linha-alvo"' if a["eh_alvo"] else ""
        setor_html = f'<div class="setor">{a["setor"]}</div>' if a.get("setor") else ""
        if a["eh_alvo"]:
            qtd_html = preco_medio_html = total_atual_html = resultado_html = '<span class="texto-apagado">—</span>'
        else:
            qtd_html = mascarar_qtd(a["qtd_total"], ocultar_valores)
            preco_medio_html = formatar_moeda_priv(a["preco_medio_ponderado"], ocultar_valores)
            total_atual_html = formatar_moeda_priv(a["atual"], ocultar_valores)
            cor = "#34d399" if a["lucro_reais"] >= 0 else "#fb7185"
            sinal = "+" if a["lucro_reais"] >= 0 else ""
            resultado_html = (
                f'<span style="color:{cor};font-weight:600">{sinal}{formatar_moeda_priv(a["lucro_reais"], ocultar_valores)} '
                f'({sinal}{formatar_pct(a["lucro_pct"])})</span>'
            )

        cotacao_html = formatar_moeda_priv(a["cotacao_atual"], False) if a["cotacao_atual"] is not None else '<span class="texto-apagado">—</span>'
        preco_teto_html = formatar_moeda_priv(a["preco_teto"], False) if a["preco_teto"] else '<span class="texto-apagado">— sem preço teto</span>'
        margem_html = formatar_moeda_priv(a["preco_teto_com_margem"], False) if a["preco_teto_com_margem"] else '<span class="texto-apagado">— sem preço teto</span>'

        motivo_texto = {"sem_preco_teto": "— sem preço teto", "sem_cotacao": "— sem cotação"}.get(a["motivo_sem_indicacao"])
        indicacao_html = badge_indicacao(a["indicacao"], motivo_texto)

        if a["margem_vs_preco_medio"] is None:
            margem_pm_html = '<span class="texto-apagado">— sem preço teto</span>' if not a["eh_alvo"] else '<span class="texto-apagado">—</span>'
        else:
            positivo = a["margem_vs_preco_medio"] >= 0
            cor = "#34d399" if positivo else "#fb7185"
            sinal = "+" if positivo else ""
            margem_pm_html = f'<span style="color:{cor};font-weight:600">{"✅" if positivo else "⚠️"} {sinal}{formatar_pct(a["margem_vs_preco_medio"])}</span>'

        alerta_html = badge_alerta(a["preco_alvo"], a["cotacao_atual"], lambda v: formatar_moeda_priv(v, False))
        variacao_html = badge_variacao_dia(a["variacao_dia_pct"])

        linhas.append(
            f'<tr{classe_linha}>'
            f'<td><span class="ticker">{a["ticker"]}{" 🎯" if a["eh_alvo"] else ""}</span>{setor_html}</td>'
            f'<td>{qtd_html}</td><td>{preco_medio_html}</td><td>{cotacao_html}</td><td>{variacao_html}</td>'
            f'<td>{alerta_html}</td>'
            f'<td>{preco_teto_html}</td><td>{margem_html}</td><td>{indicacao_html}</td><td>{margem_pm_html}</td>'
            f'<td>{total_atual_html}</td><td>{resultado_html}</td>'
            f'</tr>'
        )

    # "Alerta" fica logo cedo na tabela (antes de Preço Teto) de propósito —
    # tabelas largas como esta ficam maiores que a tela em notebooks comuns
    # e as últimas colunas exigem rolar pro lado; como o alerta é algo que
    # você quer bater o olho rapidinho, ele não pode ficar escondido lá no
    # fim, dependendo de rolagem horizontal pra aparecer.
    colunas = [
        "Ticker / Setor", "Qtd", "Preço Médio", "Cotação Atual", "Variação Dia", "Alerta", "Preço Teto",
        "Margem de Segurança (20%)", "Indicação", "Margem vs Preço Médio", "Total Atual", "Resultado",
    ]
    tabela_html = f"""
    <div style="overflow-x:auto">
    <table class="tabela-carteira">
        <thead><tr>{''.join(f'<th>{c}</th>' for c in colunas)}</tr></thead>
        <tbody>{''.join(linhas)}</tbody>
    </table>
    </div>
    """
    st.markdown(tabela_html, unsafe_allow_html=True)


def _lista_remover_ativo(lista_ativos: list[dict], dados: dict, salvar) -> None:
    """Botão de remoção total de um ativo (compra+venda+eventos), igual ao 🗑️ do dashboard original."""
    tickers = [a["ticker"] for a in lista_ativos]
    with st.expander("🗑️ Remover um ativo por completo"):
        st.caption(
            "Remove TODAS as compras/vendas e eventos societários do ticker escolhido. "
            "Se você só vendeu a posição e quer manter o histórico de lucro realizado, "
            "registre uma venda em vez de usar isto."
        )
        ticker_remover = st.selectbox("Ativo", tickers, key="sel_ticker_remover")
        confirmar = st.checkbox(f"Confirmo que quero apagar todos os registros de {ticker_remover}", key="chk_confirma_remocao")
        if st.button("Remover definitivamente", disabled=not confirmar, type="secondary"):
            dados["compras"] = [c for c in dados["compras"] if c["ticker"] != ticker_remover]
            dados["eventos"] = [e for e in dados["eventos"] if e["ticker"] != ticker_remover]
            if ticker_remover in dados["watchlist"]:
                dados["watchlist"].remove(ticker_remover)
            salvar(dados)
            st.success(f"{ticker_remover} removido.")
            st.rerun()
