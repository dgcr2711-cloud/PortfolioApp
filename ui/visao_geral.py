"""
Aba "🏠 Visão Geral" — resumo de todos os recursos numa tela só (mesmos 5
cards e a mesma tabela compacta com posições + empresas-alvo do dashboard
original).
"""

from __future__ import annotations

import streamlit as st

from core import calculations as calc
from core import portfolio_analytics as analytics
from core.config import COR_DESTAQUE, COR_NEGATIVO, COR_NEUTRO, COR_POSITIVO
from core.formatting import formatar_moeda_priv, formatar_numero, formatar_pct
from ui.ativos import montar_lista_ativos
from ui.styles import (
    badge_alerta,
    badge_indicacao,
    card_kpi_html,
    linha_diagnostico_html,
    painel_diagnostico_html,
    render_cards,
)


def render(dados: dict, ocultar_valores: bool) -> None:
    st.title("Visão Geral")
    st.caption("Resumo de todos os recursos numa tela só — para detalhes, abra a aba específica")

    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    totais = calc.totais_carteira(posicoes)
    proventos_12m = calc.proventos_12m(dados["proventos"])

    alertas = dados["alertas"]
    lista_ativos = montar_lista_ativos(dados)
    atingidos = 0
    # Conta quantos alertas foram atingidos, olhando a cotação atual de cada ativo já calculado.
    # Mesmo critério de ui/styles.py:badge_alerta — é um alerta de "preço que
    # eu quero comprar", então conta como atingido quando a cotação CAI até o
    # preço-alvo (ou abaixo), não quando sobe acima dele.
    cotacao_por_ticker = {a["ticker"]: a["cotacao_atual"] for a in lista_ativos}
    for ticker, alvo in alertas.items():
        cot = cotacao_por_ticker.get(ticker)
        if cot is not None and cot <= alvo:
            atingidos += 1

    n_carteira = sum(1 for a in lista_ativos if not a["eh_alvo"])
    n_alvo = sum(1 for a in lista_ativos if a["eh_alvo"])

    cor_lucro = "#34d399" if totais["lucro"] >= 0 else "#fb7185"
    sinal = "+" if totais["lucro"] >= 0 else ""

    render_cards([
        card_kpi_html(
            "Patrimônio Atual", formatar_moeda_priv(totais["total_atual"], ocultar_valores),
            cor_valor=COR_DESTAQUE, destaque=True,
        ),
        card_kpi_html(
            "Resultado",
            f"{sinal}{formatar_moeda_priv(totais['lucro'], ocultar_valores)}",
            cor_valor=cor_lucro,
            subvalor=f"{sinal}{formatar_pct(totais['rentabilidade_pct'])}",
            cor_sub=cor_lucro,
        ),
        card_kpi_html("Proventos (12m)", formatar_moeda_priv(proventos_12m, ocultar_valores)),
        card_kpi_html("Alertas Atingidos", f"{atingidos} / {len(alertas)}"),
        card_kpi_html("Ativos Monitorados", f"{n_carteira} na carteira + {n_alvo} alvo(s)"),
    ])

    _render_diagnostico_carteira(dados, posicoes)

    st.subheader("Todos os ativos (posições + alvo)")

    if not lista_ativos:
        st.info("Nenhum ativo ainda — registre uma compra ou adicione uma empresa alvo na aba Carteira.")
        return

    linhas_html = []
    for a in lista_ativos:
        classe_linha = ' class="linha-alvo"' if a["eh_alvo"] else ""
        tipo_texto = '<span class="texto-apagado">🎯 Alvo</span>' if a["eh_alvo"] else '<span class="texto-apagado">Posição</span>'
        cotacao_texto = formatar_moeda_priv(a["cotacao_atual"], False) if a["cotacao_atual"] is not None else '<span class="texto-apagado">—</span>'
        if a["preco_teto"] is None:
            preco_teto_texto = '<span class="texto-apagado">— sem preço teto</span>'
            preco_teto_margem_texto = '<span class="texto-apagado">—</span>'
        else:
            preco_teto_texto = formatar_moeda_priv(a["preco_teto"], False)
            # Preço-teto JÁ com a margem de segurança descontada — é este o
            # número que vale como "preço bom pra comprar", não o Preço Teto
            # cru ao lado (que é só o valor justo calculado, sem desconto de
            # segurança nenhum). Mostrar os dois lado a lado evita a leitura
            # errada de "dá pra comprar até o Preço Teto".
            preco_teto_margem_texto = formatar_moeda_priv(a["preco_teto_com_margem"], False)
        motivo_texto = {
            "sem_preco_teto": "— sem preço teto",
            "sem_cotacao": "— sem cotação",
        }.get(a["motivo_sem_indicacao"])
        indicacao_html = badge_indicacao(a["indicacao"], motivo_texto)
        alerta_html = badge_alerta(a["preco_alvo"], a["cotacao_atual"], lambda v: formatar_moeda_priv(v, False))
        linhas_html.append(
            f'<tr{classe_linha}>'
            f'<td class="ticker">{a["ticker"]}</td>'
            f'<td>{tipo_texto}</td>'
            f'<td>{cotacao_texto}</td>'
            f'<td>{alerta_html}</td>'
            f'<td>{preco_teto_texto}</td>'
            f'<td>{preco_teto_margem_texto}</td>'
            f'<td>{indicacao_html}</td>'
            f'</tr>'
        )

    tabela_html = f"""
    <table class="tabela-carteira">
        <thead><tr><th>Ticker</th><th>Tipo</th><th>Cotação</th><th>Alerta</th><th>Preço Teto</th><th>Preço Teto c/ Margem (20%)</th><th>Indicação</th></tr></thead>
        <tbody>{''.join(linhas_html)}</tbody>
    </table>
    """
    st.markdown(tabela_html, unsafe_allow_html=True)


def _render_diagnostico_carteira(dados: dict, posicoes: list[dict]) -> None:
    """
    'Painel de Diagnóstico da Carteira': a leitura em nível de carteira que
    um investidor institucional faz antes de olhar ativo por ativo —
    concentração de risco, diversificação setorial, crescimento anualizado,
    pior queda já registrada e a "qualidade média" dos fundamentos. Só
    aparece quando há posições suficientes para dizer algo com sentido.
    """
    if not posicoes:
        return

    st.subheader("🏛️ Diagnóstico da Carteira")
    st.caption("Leitura em nível de carteira — a mesma análise de concentração e qualidade que um gestor institucional faria antes de olhar ativo por ativo.")

    col_esq, col_dir = st.columns(2)

    # --- Coluna esquerda: concentração e diversificação ---------------
    concentracao = analytics.concentracao_por_ativo(posicoes)
    diag = analytics.diagnostico_concentracao(concentracao)
    setores_carteira = dados.get("setores", {})
    diversificacao = analytics.diversificacao_setorial(posicoes, setores_carteira)

    cor_classificacao = {"baixa": COR_POSITIVO, "moderada": COR_DESTAQUE, "alta": COR_NEGATIVO}[diag.classificacao_hhi]
    linhas_concentracao = [
        linha_diagnostico_html(
            "Maior posição individual",
            f"{diag.maior_ticker} — {formatar_pct(diag.maior_peso_pct)}",
            COR_NEGATIVO if diag.alerta_concentracao else "#ffffff",
        ),
        linha_diagnostico_html(
            "Índice de concentração (HHI)",
            f"{formatar_numero(diag.indice_hhi, 3)} — {diag.classificacao_hhi}",
            cor_classificacao,
        ),
    ]
    if diversificacao:
        maior_setor = diversificacao[0]
        linhas_concentracao.append(
            linha_diagnostico_html("Maior exposição setorial", f"{maior_setor['setor']} — {formatar_pct(maior_setor['peso_pct'])}")
        )
        linhas_concentracao.append(
            linha_diagnostico_html("Nº de setores distintos", str(len(diversificacao)))
        )
    selo = (
        "⚠️ Concentração acima do limite recomendado — considere diversificar novos aportes."
        if diag.alerta_concentracao
        else "✅ Nenhum ativo isolado ultrapassa o limite de concentração configurado."
    )
    with col_esq:
        st.markdown(painel_diagnostico_html("Concentração &amp; Diversificação", linhas_concentracao, selo), unsafe_allow_html=True)

    # --- Coluna direita: desempenho no tempo e fundamentos ponderados --
    cagr = analytics.cagr_aproximado(dados.get("historico", []))
    drawdown = analytics.maior_perda_registrada(dados.get("historico", []))
    fundamentos_pond = analytics.fundamentos_ponderados(posicoes, dados.get("fundamentos", {}))

    linhas_desempenho = []
    if cagr is not None:
        cor_cagr = COR_POSITIVO if cagr >= 0 else COR_NEGATIVO
        linhas_desempenho.append(linha_diagnostico_html("Crescimento anualizado (CAGR aprox.)", formatar_pct(cagr), cor_cagr))
    else:
        linhas_desempenho.append(linha_diagnostico_html("Crescimento anualizado (CAGR aprox.)", "— histórico insuficiente (mín. ~30 dias)", COR_NEUTRO))
    if drawdown is not None:
        cor_dd = COR_NEUTRO if drawdown == 0 else COR_NEGATIVO
        linhas_desempenho.append(linha_diagnostico_html("Maior perda registrada (drawdown)", formatar_pct(drawdown), cor_dd))

    if fundamentos_pond["cobertura_pct"] > 0:
        linhas_desempenho.append(linha_diagnostico_html("P/L médio ponderado", formatar_numero(fundamentos_pond["pl"], 1) if fundamentos_pond["pl"] is not None else "—"))
        linhas_desempenho.append(linha_diagnostico_html("P/VP médio ponderado", formatar_numero(fundamentos_pond["pvp"], 2) if fundamentos_pond["pvp"] is not None else "—"))
        dy = fundamentos_pond["dividend_yield"]
        linhas_desempenho.append(linha_diagnostico_html("Dividend Yield médio ponderado", formatar_pct(dy * 100) if dy is not None else "—", COR_DESTAQUE))
        roe = fundamentos_pond["roe"]
        linhas_desempenho.append(linha_diagnostico_html("ROE médio ponderado", formatar_pct(roe * 100) if roe is not None else "—"))
        selo_fund = f"Cobertura: fundamentos disponíveis para {formatar_pct(fundamentos_pond['cobertura_pct'])} do patrimônio."
    else:
        linhas_desempenho.append(
            linha_diagnostico_html("Fundamentos ponderados (P/L, P/VP, DY, ROE)", "— busque na aba 🔎 Fundamentos", COR_NEUTRO)
        )
        selo_fund = None

    with col_dir:
        st.markdown(painel_diagnostico_html("Desempenho &amp; Qualidade Fundamentalista", linhas_desempenho, selo_fund), unsafe_allow_html=True)
