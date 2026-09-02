"""
Aba "📅 Proventos" — registro manual de dividendos/JCP/rendimentos, Yield
on Cost, e os proventos já anunciados oficialmente pela B3.

Layout condensado e "de corretora" (a pedido de Diego, ago/2026): os KPIs
mais importantes ficam em destaque no topo (mesmo componente visual das
outras abas — card_kpi_html/render_cards), o resumo "por tipo" virou uma
linha compacta de badges (não mais 3 métricas grandes), e o conteúdo mais
denso/analítico (Mapa de Dividendos, formulário de registro manual,
histórico completo) foi movido para dentro de expanders — some da tela até
que o usuário queira abrir, mas continua tudo lá, um clique de distância.
Texto explicativo longo virou tooltip (parâmetro `help=` do Streamlit, o
"ⓘ" ao lado do texto) em vez de ficar sempre visível na tela.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from datetime import date, datetime, timedelta

from core import b3_publico
from core import calculations as calc
from core import data_store
from core.config import COR_DESTAQUE, DATA_INICIO_CARTEIRA
from core.formatting import formatar_data_br, formatar_moeda, formatar_moeda_priv, formatar_numero, formatar_pct
from ui import acoes_comuns, exportacao
from ui.styles import badge_html, card_kpi_html, render_cards

_NOMES_MESES = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

_NOMES_DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"]

# Cor do badge de cada tipo no resumo "Por tipo" — mesmas classes de
# ui.styles (badge-ok/info/destaque), só pra dar uma pista visual (verde/
# azul/dourado) de qual tipo é qual, sem exigir uma legenda separada.
_CORES_BADGE_TIPO = {"Dividendo": "ok", "JCP": "info", "Rendimento": "destaque"}


def render(dados: dict, ocultar_valores: bool, salvar) -> None:
    st.title("📅 Proventos")

    total_investido_atual = sum(p["valor_total_investido"] for p in calc.consolidar_posicoes(dados["compras"], dados["eventos"]))
    resumo = calc.resumo_proventos(dados["proventos"], total_investido_atual)

    render_cards([
        card_kpi_html(
            "Yield on Cost (12m)", formatar_pct(resumo["yield_on_cost"]),
            cor_valor=COR_DESTAQUE, destaque=True,
        ),
        card_kpi_html("Recebido (12m)", formatar_moeda_priv(resumo["total_12m"], ocultar_valores)),
        card_kpi_html("Total histórico", formatar_moeda_priv(resumo["total_geral"], ocultar_valores), cor_valor="#d1d5db"),
    ])
    _render_resumo_por_tipo(dados["proventos"], ocultar_valores)

    _render_proximos_dividendos(dados, salvar, ocultar_valores)
    _render_mapa_dividendos(dados, ocultar_valores)

    st.divider()
    with st.expander("➕ Registrar provento manualmente"):
        _render_form_registrar(dados, salvar)

    _render_historico(dados, ocultar_valores, salvar)


def _render_resumo_por_tipo(proventos: list[dict], ocultar_valores: bool) -> None:
    """
    De onde vem o total recebido — Dividendo x JCP x Rendimento — como uma
    linha compacta de badges (não mais 3 st.metric grandes): é um contexto
    rápido, não outro número disputando atenção com o Yield on Cost em
    destaque logo acima.
    """
    linhas_tipo = calc.resumo_proventos_por_tipo(proventos)
    if not linhas_tipo:
        return

    # Dentro de um st.container(border=True) — 2026-09-02: antes as pílulas
    # ficavam soltas direto no fundo da página, e com só 1 tipo registrado
    # (comum no início) sobrava um vão vazio enorme ao lado, parecendo algo
    # quebrado/incompleto. Um cartão com borda dá um contorno claro pro
    # conteúdo, do mesmo jeito que o resto do app, mesmo com 1 pílula só.
    with st.container(border=True):
        st.caption(
            "Por tipo",
            help=(
                "Bonificação não entra aqui: é recebida como ações novas (não dinheiro) e já aparece "
                "como evento societário na aba 🧾 Compras & Vendas."
            ),
        )
        total_geral = sum(l["total"] for l in linhas_tipo)
        pilulas = []
        for linha in linhas_tipo:
            pct = (linha["total"] / total_geral * 100) if total_geral else 0.0
            valor_texto = formatar_moeda_priv(linha["total"], ocultar_valores)
            tipo_badge = _CORES_BADGE_TIPO.get(linha["tipo"], "neutral")
            pilulas.append(badge_html(f"{linha['tipo']} · {formatar_pct(pct)} · {valor_texto}", tipo_badge))
        st.markdown(f'<div class="linha-badges">{"".join(pilulas)}</div>', unsafe_allow_html=True)


def _opacidade_mes_pago(contagem: int) -> float:
    """Quanto mais vezes um ativo pagou naquele mês (no seu histórico), mais forte o verde da célula."""
    return min(0.16 + 0.14 * (contagem - 1), 0.60)


def _render_mapa_dividendos(dados: dict, ocultar_valores: bool) -> None:
    """
    Painel 'Mapa de Dividendos': grade Ticker x Mês, agrupada por setor —
    dentro de um expander (fechado por padrão) porque é conteúdo denso e
    analítico, não algo que precisa aparecer assim que a aba abre.

    🟢 verde sólido = mês em que você já REGISTROU um provento no seu
    histórico. 🔵 azul tracejado = mês em que a própria B3 já ANUNCIOU
    oficialmente um pagamento (últimos ~12-14 meses, buscado sozinho junto
    com "🔄 Atualizar Dados" — ver core/b3_publico.py e
    ui.acoes_comuns.atualizar_proventos_b3) e que ainda não está no seu
    histórico registrado. Um ativo nunca registrado manualmente, mas com
    provento já anunciado pela B3, aparece mesmo assim ("linha só automática").
    """
    proventos = dados["proventos"]
    mapa = calc.mapa_dividendos_por_ticker(proventos, data_minima=DATA_INICIO_CARTEIRA)
    anunciados = dados.get("proventosAnunciadosB3") or {}
    meses_auto = b3_publico.meses_anunciados_por_ticker(anunciados, data_minima=DATA_INICIO_CARTEIRA)
    if not mapa and not meses_auto:
        return

    with st.expander("🗓️ Mapa de Dividendos — histórico mês a mês"):
        st.caption(
            "🟢 já registrado · 🔵 anunciado pela B3 (ainda não registrado) · a partir de "
            f"{formatar_data_br(DATA_INICIO_CARTEIRA)}",
            help=(
                'Atualizado sozinho junto com "🔄 Atualizar Dados" (no máx. 1x por dia). A parte '
                "azul só cobre o ciclo mais recente anunciado pela B3 — não substitui anos de "
                "histórico registrado manualmente."
            ),
        )

        setores = dados.get("setores", {})
        por_ticker = {item["ticker"]: item for item in mapa}
        todos_tickers = set(por_ticker) | set(meses_auto)
        grupos: dict[str, list[str]] = {}
        for ticker in todos_tickers:
            setor = setores.get(ticker) or "Sem setor definido"
            grupos.setdefault(setor, []).append(ticker)

        linhas_html = []
        for setor in sorted(grupos.keys()):
            linhas_html.append(f'<tr class="linha-setor"><td colspan="13">{setor}</td></tr>')
            for ticker in sorted(grupos[setor]):
                item = por_ticker.get(ticker)
                meses_auto_ticker = set(meses_auto.get(ticker, []))
                classe_linha = "" if item else ' class="linha-so-automatica"'
                celulas = []
                for mes in range(1, 13):
                    contagem = item["contagem_por_mes"].get(mes, 0) if item else 0
                    if contagem > 0:
                        opacidade = _opacidade_mes_pago(contagem)
                        titulo = f'{contagem}x em {_NOMES_MESES[mes - 1]} (registrado)'
                        if mes in meses_auto_ticker:
                            titulo += " · também anunciado pela B3"
                        celulas.append(f'<td class="mes-pago" style="background:rgba(52,211,153,{opacidade})" title="{titulo}">$</td>')
                    elif mes in meses_auto_ticker:
                        titulo = f'{_NOMES_MESES[mes - 1]}: anunciado pela B3 (automático, ainda não registrado)'
                        celulas.append(f'<td class="mes-anunciado" style="background:rgba(56,189,248,0.18)" title="{titulo}">$</td>')
                    else:
                        celulas.append('<td class="mes-vazio">·</td>')
                linhas_html.append(f'<tr{classe_linha}><td class="col-ticker">{ticker}</td>{"".join(celulas)}</tr>')

        cabecalho_meses = "".join(f"<th>{m}</th>" for m in _NOMES_MESES)
        tabela_html = f"""
        <table class="mapa-dividendos">
            <thead><tr><th class="col-ticker">Ticker</th>{cabecalho_meses}</tr></thead>
            <tbody>{''.join(linhas_html)}</tbody>
        </table>
        """
        st.markdown(tabela_html, unsafe_allow_html=True)

        avisos = []
        if any(item["quantidade_pagamentos"] < 2 for item in mapa):
            avisos.append(
                "ativo(s) com só 1 pagamento registrado: o verde ali é só aquele único pagamento, "
                "ainda não dá pra confirmar o padrão"
            )
        if any(t not in por_ticker for t in meses_auto):
            avisos.append("ticker(s) só com célula azul: a B3 já anunciou, mas você ainda não registrou nenhum provento dele")
        if avisos:
            st.caption("⚠️ " + " · ".join(avisos) + ".")

        if st.checkbox("📊 Ver valor médio por pagamento, ativo por ativo", key="chk_valor_medio_mapa"):
            linhas_tabela = [
                {
                    "Ticker": item["ticker"],
                    "Meses que costuma pagar": ", ".join(_NOMES_MESES[m - 1] for m in item["meses"]),
                    "Valor médio por pagamento": formatar_moeda_priv(item["valor_medio_por_pagamento"], ocultar_valores),
                    "Pagamentos registrados": item["quantidade_pagamentos"],
                }
                for item in mapa
            ]
            st.dataframe(pd.DataFrame(linhas_tabela), use_container_width=True, hide_index=True)

        fluxo = calc.fluxo_mensal_estimado_dividendos(proventos, data_minima=DATA_INICIO_CARTEIRA)
        if not ocultar_valores:
            fig = go.Figure(go.Bar(x=_NOMES_MESES, y=fluxo, marker_color=COR_DESTAQUE))
            fig.update_layout(
                title="Fluxo estimado de proventos por mês",
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=260, margin=dict(l=10, r=10, t=40, b=10), yaxis_tickprefix="R$ ",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Estimativa com base no valor médio já recebido nos meses em que cada ativo "
                "historicamente pagou — a empresa pode mudar (ou parar) a política de dividendos a "
                "qualquer momento, não é promessa de recebimento."
            )


def _render_proximos_dividendos(dados: dict, salvar, ocultar_valores: bool) -> None:
    """
    Painel 'Próximos Dividendos': dividendos/JCP/rendimentos já anunciados
    pelas empresas da carteira + watchlist, com valor por ação e data de
    pagamento reais — direto do site oficial da B3, sem login e sem custo
    (ver core/b3_publico.py). Layout em cards agrupados (Carteira/
    Watchlist), inspirado no app "Agenda Dividendos" mostrado como
    referência por Diego, nas cores do tema escuro do resto deste app.

    "Carteira" multiplica o valor por ação pela quantidade que você tinha
    na "Data Com" de cada provento (calc.enriquecer_proximos_com_total) —
    é o valor que você deve receber de fato; um ativo comprado DEPOIS da
    Data Com de um provento já anunciado aparece marcado "sem direito"
    mesmo que você já o possua hoje. "Watchlist" mostra o que foi anunciado
    pra ativos que você só acompanha, sem coluna de Total — fica dentro de
    um expander fechado por padrão (é conteúdo secundário; "Carteira" acima
    continua sempre visível, é dinheiro que você de fato vai receber).

    100% automático: dados["proventosAnunciadosB3"] é buscado e mantido em
    dia sozinho, junto com "🔄 Atualizar Dados" (no máx. 1x/dia — ver
    ui.acoes_comuns.atualizar_proventos_b3); o botão aqui só serve pra
    quem quiser forçar uma busca na hora, ignorando esse limite.
    """
    col_titulo, col_botao = st.columns([5, 2])
    col_titulo.subheader("📬 Próximos Dividendos")
    atualizado_em = dados.get("proventosAnunciadosB3AtualizadoEm")
    ajuda = (
        "Direto do site oficial da B3, sem login e sem custo — atualizado sozinho junto com "
        '"🔄 Atualizar Dados" (no máx. 1x por dia). "Sem direito" = você comprou o ativo DEPOIS da '
        "Data Com desse provento específico (passe o mouse na linha pra ver a data), mesmo já "
        "possuindo o ativo hoje."
    )
    if atualizado_em:
        quando = datetime.fromisoformat(atualizado_em).strftime("%d/%m %H:%M")
        col_titulo.caption(f"Atualizado às {quando}", help=ajuda)
    else:
        col_titulo.caption("Ainda não buscado nesta carteira.", help=ajuda)
    if col_botao.button("🔍 Buscar agora", use_container_width=True):
        acoes_comuns.atualizar_proventos_b3(dados, salvar, forcar=True)
        st.rerun()
    acoes_comuns.exibir_status_proventos_b3()

    anunciados = dados.get("proventosAnunciadosB3") or {}
    proximos = b3_publico.proximos_a_partir_de(anunciados, hoje=date.today())
    if not proximos:
        # Estado vazio dentro de um cartão com borda (2026-09-02) — antes
        # era só uma legenda solta embaixo do botão "🔍 Buscar agora", sem
        # nenhum contorno visual ligando as duas coisas; parecia que a
        # seção tinha "quebrado" em vez de simplesmente não ter dados
        # ainda. Mensagem também ficou mais convidativa (indica a ação).
        with st.container(border=True):
            if atualizado_em:
                st.caption("📭 Nenhum pagamento futuro anunciado pela B3 no momento para os ativos consultados.")
            else:
                st.caption(
                    '🔍 Ainda não buscamos os próximos dividendos desta carteira — clique em '
                    '"Buscar agora" acima (ou espere a próxima 🔄 Atualizar Dados, no máx. 1x por dia) '
                    "pra ver os pagamentos já anunciados pela B3."
                )
        return

    enriquecidos = calc.enriquecer_proximos_com_total(
        proximos, dados["compras"], dados["eventos"], hoje=date.today().isoformat()
    )
    carteira = [p for p in enriquecidos if p["quantidade_hoje"] > 0]
    watchlist = [p for p in enriquecidos if p["quantidade_hoje"] <= 0]

    _render_calendario_proventos(enriquecidos, ocultar_valores)

    with st.expander("📜 Ver lista completa (além dos próximos dias úteis)"):
        if carteira:
            _render_card_proximos("📈 Carteira", carteira, ocultar_valores, mostrar_total=True)
            if any(p["sem_direito"] for p in carteira):
                st.caption('⚠️ "sem direito" = comprado depois da Data Com — não vale pra esse provento específico.')
        _render_watchlist_proximos(watchlist, ocultar_valores)


def _proximos_dias_uteis(hoje: date, quantidade: int) -> list[date]:
    """Os próximos `quantidade` dias ÚTEIS (seg-sex) a partir de hoje, hoje incluso se for dia útil."""
    dias: list[date] = []
    cursor = hoje
    while len(dias) < quantidade:
        if cursor.weekday() < 5:
            dias.append(cursor)
        cursor += timedelta(days=1)
    return dias


def _eventos_por_dia(itens: list[dict], dias_iso: set[str]) -> dict[str, list[dict]]:
    """
    Agrupa por data (ISO) os eventos de Data Com e Pagamento de cada
    provento anunciado, só dentro dos dias úteis mostrados no calendário.
    Um mesmo provento pode gerar até 2 eventos (a Data Com e o Pagamento
    caem em dias diferentes) — cada um com sua própria "cor" na Agenda.

    O valor mostrado em cada evento é sempre dinheiro de verdade, não o
    valor por ação cru: pra um ativo da carteira COM direito (você já
    tinha a quantidade que valeu pra esse provento), mostra o TOTAL
    (valor por ação × sua quantidade) tanto na Data Com quanto no
    Pagamento — 2026-09-03, a pedido de Diego ("provento que será pago é
    uma coisa, valor em R$ é o valor do provento x nº de ações": o card
    tem que mostrar o dinheiro de verdade, não o valor por ação isolado).
    Só mostra o valor por ação isolado quando não há uma quantidade real
    por trás dele: ativo de watchlist (você não possui) ou "sem direito"
    (comprou depois da Data Com — não vale pra esse provento específico).
    """
    eventos: dict[str, list[dict]] = {d: [] for d in dias_iso}
    for item in itens:
        is_watchlist = item["quantidade_hoje"] <= 0
        por_acao = is_watchlist or item["sem_direito"]
        if item.get("data_com") in dias_iso:
            eventos[item["data_com"]].append({
                "ticker": item["ticker"], "tipo": item["tipo"], "evento": "data_com",
                "valor": item["valor_por_acao"] if por_acao else item["total"],
                "is_watchlist": is_watchlist, "sem_direito": item["sem_direito"],
            })
        if item["data_pagamento"] in dias_iso:
            eventos[item["data_pagamento"]].append({
                "ticker": item["ticker"], "tipo": item["tipo"], "evento": "pagamento",
                "valor": item["valor_por_acao"] if por_acao else item["total"],
                "is_watchlist": is_watchlist, "sem_direito": item["sem_direito"],
            })
    for lista in eventos.values():
        lista.sort(key=lambda e: (e["evento"] != "pagamento", e["ticker"]))
    return eventos


def _render_calendario_proventos(itens: list[dict], ocultar_valores: bool) -> None:
    """
    "Agenda de Dividendos" — a Data Com e o Pagamento de cada provento
    anunciado, plotados nos próprios dias úteis em que caem (próximos 5),
    no estilo do app "Agenda Dividendos" que Diego mostrou como
    referência (2026-09-02). Dourado = Data Com (é até quando você
    precisava ter comprado pra ter direito) · Verde = Pagamento (dinheiro
    cai na conta). Em ambos, o valor mostrado é sempre o TOTAL em R$ (valor
    por ação × sua quantidade) pra ativos da carteira com direito — só
    aparece o valor por ação isolado quando não há uma quantidade real por
    trás: watchlist ou "sem direito" (ver docstring de _eventos_por_dia).
    👀 marca um ativo que você só acompanha, não é posição sua. Só olha os
    próximos dias úteis por padrão — o resto continua disponível no
    expander "Ver lista completa" logo abaixo, pra não perder nada que já
    estava sendo mostrado antes.

    Só entram na faixa os dias que já têm algum evento (Data Com ou
    Pagamento) — dia útil sem nada anunciado simplesmente não aparece,
    em vez de virar um cartão vazio (a pedido de Diego, 2026-09-02).
    """
    hoje = date.today()
    dias = _proximos_dias_uteis(hoje, 5)
    dias_iso = {d.isoformat() for d in dias}
    eventos = _eventos_por_dia(itens, dias_iso)

    dias_com_eventos = [d for d in dias if eventos[d.isoformat()]]
    if not dias_com_eventos:
        return

    colunas_html = []
    for d in dias_com_eventos:
        d_iso = d.isoformat()
        classe_hoje = " cal-hoje" if d == hoje else ""
        nome_dia = "Hoje" if d == hoje else _NOMES_DIAS_SEMANA[d.weekday()]
        cartoes = []
        for ev in eventos[d_iso]:
            tipo_badge = "ok" if ev["evento"] == "pagamento" else "destaque"
            rotulo_evento = "Pagamento" if ev["evento"] == "pagamento" else "Data Com"
            if ev["sem_direito"]:
                rotulo_evento += " (sem direito)"
            marca_watchlist = " 👀" if ev["is_watchlist"] else ""
            valor_texto = "••••" if ocultar_valores else formatar_moeda(ev["valor"])
            cartoes.append(
                f'<div class="cal-evento">'
                f'<div class="cal-topo">{badge_html(ev["ticker"] + marca_watchlist, tipo_badge)}'
                f'<span class="cal-valor">{valor_texto}</span></div>'
                f'<div class="cal-rotulo">{rotulo_evento} · {ev["tipo"]}</div>'
                f'</div>'
            )
        colunas_html.append(
            f'<div class="cal-dia{classe_hoje}">'
            f'<div class="cal-cabecalho"><div class="dia-semana">{nome_dia}</div>'
            f'<div class="dia-data">{d.strftime("%d/%m")}</div></div>'
            f'<div class="cal-eventos">{"".join(cartoes)}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="calendario-proventos">{"".join(colunas_html)}</div>', unsafe_allow_html=True)
    st.caption(
        "🥇 dourado = Data Com (até quando você precisava ter comprado) · 🟢 verde = Pagamento "
        "(dinheiro cai na conta) · 👀 = ativo da watchlist, não é posição sua."
    )


def _render_watchlist_proximos(watchlist: list[dict], ocultar_valores: bool) -> None:
    """
    Chamada de dentro do expander "📜 Ver lista completa" (ver
    _render_proximos_dividendos) — por isso não abre um expander próprio
    aqui dentro (o Streamlit não permite expander dentro de expander); um
    divisor + legenda já bastam pra separar visualmente da lista "Carteira"
    acima.
    """
    if watchlist:
        st.divider()
        st.caption(f"👀 Watchlist — anunciados pela B3 ({len(watchlist)})")
        _render_card_proximos("👀 Watchlist", watchlist, ocultar_valores, mostrar_total=False)


def _render_card_proximos(titulo: str, itens: list[dict], ocultar_valores: bool, mostrar_total: bool) -> None:
    """Um card do painel 'Próximos Dividendos' — ver docstring de _render_proximos_dividendos."""
    linhas_html = []
    total_grupo = 0.0
    for item in itens:
        total_grupo += item["total"]
        valor_acao_texto = "••••" if ocultar_valores else formatar_numero(item["valor_por_acao"], 4)
        # &quot; em vez de aspas normais: dentro de um atributo title="..."
        # já delimitado por aspas, uma aspa "crua" no meio do texto fecha o
        # atributo cedo e quebra o HTML (o navegador ainda tolera, mas é
        # inválido) — a entidade HTML é a forma correta de representar uma
        # aspa dentro do valor de um atributo.
        titulo_linha = f'Data &quot;Com&quot;: {formatar_data_br(item["data_com"])}' if item["data_com"] else ""
        if not mostrar_total:
            celula_total = ""
        elif item["sem_direito"]:
            celula_total = '<td class="col-total sem-direito">— sem direito</td>'
        else:
            celula_total = f'<td class="col-total">{"••••" if ocultar_valores else formatar_numero(item["total"], 2)}</td>'
        linhas_html.append(
            f'<tr title="{titulo_linha}">'
            f'<td class="col-esquerda">{formatar_data_br(item["data_pagamento"])}</td>'
            f'<td class="col-esquerda col-ticker">{item["ticker"]}</td>'
            f'<td class="col-esquerda">{item["tipo"]}</td>'
            f'<td>{valor_acao_texto}</td>'
            f'{celula_total}</tr>'
        )
    cabecalho_total = "<th>Total</th>" if mostrar_total else ""
    rodape = ""
    if mostrar_total:
        total_texto = "R$ ••••••" if ocultar_valores else formatar_moeda(total_grupo)
        rodape = f'<div class="rodape-total"><span>Total provisionado</span><strong>{total_texto}</strong></div>'
    tabela_html = f"""
    <div class="card-proximos-proventos">
        <div class="cabecalho-grupo">{titulo}</div>
        <table class="tabela-proximos-proventos">
            <thead><tr>
                <th class="col-esquerda">Dt. Pgto.</th>
                <th class="col-esquerda">Ação</th>
                <th class="col-esquerda">Tipo</th>
                <th>Vl./Ação</th>
                {cabecalho_total}
            </tr></thead>
            <tbody>{''.join(linhas_html)}</tbody>
        </table>
        {rodape}
    </div>
    """
    # Quando não tem coluna de Total (Watchlist: mostrar_total=False),
    # {cabecalho_total} e {rodape} viram string vazia -- e como cada um
    # ocupa a própria linha no modelo acima, sobra uma linha só com
    # espaços em branco no meio do HTML. Isso faz o Streamlit parar de
    # tratar o texto como HTML "cru" bem no meio (uma linha em branco
    # encerra o bloco de HTML, no Markdown) e mostrar o resto como texto
    # puro em vez de tabela -- bug real que o Diego pegou (a coluna Total
    # do card "Carteira" mascarava isso por acaso). Removendo as linhas em
    # branco evita esse corte, sem mudar nada visualmente.
    tabela_html = "\n".join(linha for linha in tabela_html.splitlines() if linha.strip())
    st.markdown(tabela_html, unsafe_allow_html=True)


def _render_form_registrar(dados: dict, salvar) -> None:
    """
    Formulário de registro manual — dentro de um expander (ver render()),
    fechado por padrão.

    2026-09-03 (a pedido de Diego, depois de reportar um provento salvo
    errado): antes pedia direto o "Valor Total (R$)", exigindo que ele
    mesmo multiplicasse valor-por-ação × quantidade de ações antes de
    digitar — fácil de errar, e foi exatamente o que aconteceu. Agora ele
    digita só o Valor por Ação (o número que aparece no comunicado da
    empresa/B3) e a quantidade que ele tinha NA DATA do provento é
    calculada sozinha a partir do histórico de compras/eventos
    (core.calculations.quantidade_em_data — mesma regra de "quantidade na
    Data Com" já usada em Próximos Dividendos). O total salvo é sempre a
    multiplicação automática das duas, mostrado antes de clicar Adicionar.
    """
    c1, c2, c3, c4 = st.columns(4)
    ticker = c1.text_input("Ticker", placeholder="Ex: PETR4", max_chars=10, key="reg_ticker").strip().upper()
    data = c2.date_input("Data", key="reg_data")
    tipo = c3.selectbox("Tipo", ["Dividendo", "JCP", "Rendimento"], key="reg_tipo")
    valor_por_acao = c4.number_input(
        "Valor por Ação (R$)", min_value=0.0, step=0.0001, format="%.4f", key="reg_valor_acao",
        help="O valor por ação anunciado pela empresa/B3 — o total é calculado sozinho logo abaixo, não precisa multiplicar nada.",
    )

    quantidade = calc.quantidade_em_data(ticker, data.isoformat(), dados["compras"], dados["eventos"]) if ticker else 0.0
    total = valor_por_acao * quantidade

    if not ticker:
        st.caption("Informe o ticker para calcular o total automaticamente.")
    elif quantidade <= 0:
        st.caption(
            f"⚠️ Você não tinha {ticker} em carteira em {formatar_data_br(data.isoformat())} "
            "(conferido pelo seu histórico de compras) — confira o ticker ou a data antes de adicionar."
        )
    else:
        st.caption(
            f"Total a registrar: **{formatar_moeda(total)}** "
            f"({formatar_numero(quantidade, 0)} ações × {formatar_moeda(valor_por_acao)}/ação)"
        )

    if st.button("Adicionar", type="primary", key="reg_adicionar"):
        if not ticker:
            st.warning("Informe o ticker.")
        elif quantidade <= 0:
            st.warning(f"Você não tinha {ticker} em carteira nessa data — confira o ticker/data antes de adicionar.")
        else:
            dados["proventos"].append({
                "id": data_store.novo_id(), "ticker": ticker, "data": data.isoformat(),
                "tipo": tipo, "valor": float(total),
            })
            salvar(dados)
            st.rerun()


def _render_historico(dados: dict, ocultar_valores: bool, salvar) -> None:
    """Tabela completa de proventos registrados — dentro de um expander (ver render()), fechado por padrão."""
    if not dados["proventos"]:
        st.caption("Nenhum provento registrado ainda.")
        return

    ordenados = sorted(dados["proventos"], key=lambda p: p["data"], reverse=True)
    linhas = [{
        "Data": formatar_data_br(p["data"]), "Ticker": p["ticker"], "Tipo": p["tipo"],
        "Valor": formatar_moeda_priv(p["valor"], ocultar_valores), "id": p["id"],
    } for p in ordenados]
    df = pd.DataFrame(linhas)

    with st.expander(f"📜 Histórico completo de proventos ({len(ordenados)})"):
        st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

        csv_proventos = exportacao.gerar_csv_proventos(dados)
        st.download_button(
            "⬇️ Baixar histórico (.csv)", data=csv_proventos,
            file_name=f"proventos-b3-{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            help="Abre no Excel/Google Sheets — separado por ';', igual ao padrão em português.",
        )

        if st.checkbox("🗑️ Remover um provento", key="chk_remover_provento"):
            opcoes = {f'{l["Data"]} · {l["Ticker"]} · {l["Tipo"]} · {l["Valor"]}': l["id"] for l in linhas}
            escolhida = st.selectbox("Provento", list(opcoes.keys()), key="sel_remover_provento")
            if st.button("Remover provento selecionado"):
                id_remover = opcoes[escolhida]
                dados["proventos"] = [p for p in dados["proventos"] if p["id"] != id_remover]
                salvar(dados)
                st.rerun()
