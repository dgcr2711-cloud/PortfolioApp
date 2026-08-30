"""
Aba "🔎 Fundamentos" — indicadores fundamentalistas (P/L, P/VP, Dividend
Yield, ROE, margens, alavancagem, valor de mercado, beta, faixa de 52
semanas) das posições da carteira e das empresas-alvo da watchlist.

Esta é a leitura clássica de "value investing": um Preço Teto (aba
🎯) diz se o PREÇO está caro ou barato; os fundamentos aqui dizem se a
EMPRESA por trás do preço é, de fato, um bom negócio — rentável, sólida e
crescendo. As duas leituras se complementam, nunca substituem uma à outra.

Separado do botão "🔄 Atualizar Dados" da barra lateral porque `.info` do
yfinance é uma consulta bem mais pesada que buscar só o preço — teria
pouco sentido repeti-la a cada 5 minutos.
"""

from __future__ import annotations

import streamlit as st

from core import altman, calculations as calc, piotroski, valuation_multiplos
from core import portfolio_analytics as analytics
from core.config import COR_DESTAQUE, COR_NEGATIVO, COR_NEUTRO, COR_POSITIVO
from core.formatting import formatar_moeda, formatar_numero, formatar_pct
from ui.acoes_comuns import (
    atualizar_analise_avancada,
    atualizar_dados_fundamentalistas,
    exibir_status_analise_avancada,
    exibir_status_fundamentos,
)
from ui.ativos import montar_lista_ativos
from ui.styles import card_kpi_html, render_cards


def render(dados: dict, salvar) -> None:
    st.title("Fundamentos")
    st.caption("Indicadores fundamentalistas das suas posições e da watchlist — a leitura de 'a empresa é um bom negócio?', complementar ao Preço Teto.")

    col_titulo, col_botao = st.columns([3, 1])
    with col_botao:
        if st.button("🔄 Atualizar Fundamentos", use_container_width=True, type="primary"):
            atualizar_dados_fundamentalistas(dados, salvar)
            st.rerun()

    exibir_status_fundamentos()

    fundamentos = dados.get("fundamentos", {})
    lista_ativos = montar_lista_ativos(dados)

    if not lista_ativos:
        st.info('Nenhum ativo ainda. Registre uma compra ou adicione uma empresa alvo na aba "📈 Carteira".')
        return

    if not fundamentos:
        st.warning('Ainda não há fundamentos buscados. Clique em "🔄 Atualizar Fundamentos" acima para buscar no Yahoo Finance.')

    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    resumo = analytics.fundamentos_ponderados(posicoes, fundamentos)

    if resumo["cobertura_pct"] > 0:
        dy = resumo["dividend_yield"]
        roe = resumo["roe"]
        render_cards([
            card_kpi_html("P/L médio ponderado", formatar_numero(resumo["pl"], 1) if resumo["pl"] is not None else "—", destaque=True),
            card_kpi_html("P/VP médio ponderado", formatar_numero(resumo["pvp"], 2) if resumo["pvp"] is not None else "—", destaque=True),
            card_kpi_html("Dividend Yield médio ponderado", formatar_pct(dy * 100) if dy is not None else "—", cor_valor=COR_DESTAQUE, destaque=True),
            card_kpi_html("ROE médio ponderado", formatar_pct(roe * 100) if roe is not None else "—", destaque=True),
            card_kpi_html("Cobertura da carteira", formatar_pct(resumo["cobertura_pct"]), cor_valor=COR_NEUTRO),
        ])
        st.caption("Médias ponderadas pelo valor atual de cada posição — ativos sem fundamento buscado ainda ficam de fora da conta (não entram como zero).")

    st.subheader("📋 Indicadores por Ativo")
    _tabela_fundamentos_html(lista_ativos, fundamentos)

    st.subheader("🎯 Indicadores para o Preço Teto")
    st.caption(
        "Os mesmos números que servem de ponto de partida pra calculadora de Fluxo de Caixa Descontado da aba 🎯 Preço Teto. "
        "O WACC, a taxa de crescimento futura (g1/g2) e a margem de segurança continuam sendo uma decisão sua — "
        "o Yahoo Finance não fornece isso pronto, só os números abaixo. "
        "⚠️ Empresas com mais de uma classe de ação (ON/PN/units — ex: Sanepar tem SAPR3/SAPR4/SAPR11) merecem atenção redobrada "
        "no 'Nº de Ações': buscamos só o dado do TICKER que você tem na carteira, nunca somamos com outra classe por aqui — mas o "
        "próprio Yahoo Finance às vezes devolve o total da empresa (todas as classes somadas) em vez de só a classe daquele ticker. "
        "Vale conferir esse número no Fundamentus ou no site de RI da empresa antes de usar na calculadora."
    )
    _tabela_indicadores_preco_teto_html(lista_ativos, fundamentos)

    st.markdown("---")
    _secao_analise_avancada(dados, salvar, lista_ativos, fundamentos)

    with st.expander("ℹ️ O que significa cada indicador"):
        st.markdown(
            "- **P/L** (Preço/Lucro): quantos anos de lucro atual seriam necessários para 'pagar' o preço da ação — quanto menor, mais barata a ação em relação ao lucro que gera hoje.\n"
            "- **P/VP** (Preço/Valor Patrimonial): compara o preço de mercado com o patrimônio líquido por ação — abaixo de 1 pode indicar desconto, mas também pode refletir um negócio de baixa qualidade.\n"
            "- **Dividend Yield**: proventos pagos nos últimos 12 meses em relação ao preço atual.\n"
            "- **Payout**: % do lucro líquido dos últimos 12 meses que a empresa distribuiu como proventos — o 'complemento' do Dividend Yield: mostra se ela reparte quase tudo que lucra (payout alto, sobra pouco pra reinvestir e crescer) ou reinveste a maior parte (payout baixo). Vem pronto do Yahoo Finance.\n"
            "- **Payout (12m calc.)**: o mesmo payout dos últimos 12 meses, só que calculado por aqui a partir das demonstrações trimestrais (dividendos pagos ÷ lucro líquido dos últimos 4 trimestres) — serve de conferência do Payout acima. Pode aparecer '—' quando faltar algum trimestre no histórico do Yahoo Finance (mais comum em empresas da B3 do que dos EUA).\n"
            "- **ROE** (Retorno sobre o Patrimônio): quanto lucro a empresa gera para cada R$1 de patrimônio líquido — uma das métricas favoritas de investidores de valor para medir a qualidade do negócio.\n"
            "- **Margem Líquida**: % da receita que sobra como lucro, depois de todos os custos e impostos.\n"
            "- **Dívida/Patrimônio**: o quanto a empresa depende de dívida em relação ao capital próprio — quanto maior, maior o risco financeiro.\n"
            "- **Beta**: sensibilidade histórica do preço em relação ao mercado (Ibovespa) — acima de 1 tende a oscilar mais que o mercado, abaixo de 1, menos.\n"
            "- **FCF Livre (Fluxo de Caixa Livre)**: o caixa que sobra da operação depois dos investimentos necessários pro negócio funcionar — é o ponto de partida ('FCF do último ano') da calculadora de Preço Teto.\n"
            "- **Dívida Líquida**: dívida total menos o caixa disponível — usada na calculadora de Preço Teto pra ir do valor da empresa inteira ao valor que sobra pro acionista.\n"
            "- **Nº de Ações**: ações em circulação DO TICKER que você tem — buscamos só o dado dessa listagem específica, nunca somamos com outra classe (ON/PN/units) por aqui. Ainda assim, pra empresas com mais de uma classe (ex: Sanepar: SAPR3/SAPR4/SAPR11), o próprio Yahoo Finance às vezes reporta o total da empresa em vez de só essa classe — vale conferir no Fundamentus ou no RI da empresa antes de usar na calculadora de Preço Teto."
        )


def _tabela_fundamentos_html(lista_ativos: list[dict], fundamentos: dict[str, dict]) -> None:
    linhas = []
    for a in lista_ativos:
        ticker = a["ticker"]
        f = fundamentos.get(ticker)
        classe_linha = ' class="linha-alvo"' if a["eh_alvo"] else ""
        tipo_html = ' 🎯' if a["eh_alvo"] else ""

        if not f:
            linhas.append(
                f'<tr{classe_linha}><td><span class="ticker">{ticker}{tipo_html}</span></td>'
                f'<td colspan="12"><span class="texto-apagado">— sem fundamentos buscados ainda</span></td></tr>'
            )
            continue

        def cel(valor, casas=2, sufixo=""):
            return formatar_numero(valor, casas) + sufixo if valor is not None else '<span class="texto-apagado">—</span>'

        def cel_pct(valor):
            return formatar_pct(valor * 100) if valor is not None else '<span class="texto-apagado">—</span>'

        margem_liq_html = cel_pct(f.get("margem_liquida"))
        cor_margem = COR_POSITIVO if (f.get("margem_liquida") or 0) > 0 else COR_NEGATIVO
        divida_pl = f.get("divida_patrimonio")
        cor_divida = COR_NEUTRO if divida_pl is None else (COR_POSITIVO if divida_pl < 100 else COR_NEGATIVO)

        # Setor único do app (dados["setores"]) — nunca mais o setor bruto do Yahoo
        # em inglês, que podia mostrar algo diferente do resto do app para o mesmo
        # ativo. Ver core/setores.py: o setor do Yahoo já virou uma SUGESTÃO
        # automática para dados["setores"] logo que os fundamentos são buscados.
        setor_html = f'<div class="setor">{a.get("setor")}</div>' if a.get("setor") else ""
        valor_mercado = f.get("valor_mercado")
        vm_texto = f"R$ {valor_mercado / 1e9:.1f} bi" if valor_mercado and valor_mercado >= 1e9 else (f"R$ {valor_mercado / 1e6:.0f} mi" if valor_mercado else "—")
        faixa_52s = (
            f"{formatar_numero(f.get('minima_52s'), 2)} – {formatar_numero(f.get('maxima_52s'), 2)}"
            if f.get("minima_52s") is not None and f.get("maxima_52s") is not None
            else '<span class="texto-apagado">—</span>'
        )

        linhas.append(
            f'<tr{classe_linha}>'
            f'<td><span class="ticker">{ticker}{tipo_html}</span>{setor_html}</td>'
            f'<td>{cel(f.get("pl"), 1)}</td>'
            f'<td>{cel(f.get("pl_projetado"), 1)}</td>'
            f'<td>{cel(f.get("pvp"), 2)}</td>'
            f'<td style="color:{COR_DESTAQUE};font-weight:600">{cel_pct(f.get("dividend_yield"))}</td>'
            f'<td>{cel_pct(f.get("payout_ratio"))}</td>'
            f'<td>{cel_pct(f.get("payout_ttm_calculado"))}</td>'
            f'<td>{cel_pct(f.get("roe"))}</td>'
            f'<td style="color:{cor_margem}">{margem_liq_html}</td>'
            f'<td style="color:{cor_divida}">{cel(divida_pl, 0, "%") if divida_pl is not None else "—"}</td>'
            f'<td>{vm_texto}</td>'
            f'<td>{cel(f.get("beta"), 2)}</td>'
            f'<td>{faixa_52s}</td>'
            f'</tr>'
        )

    colunas = [
        "Ticker / Setor", "P/L", "P/L proj.", "P/VP", "Div. Yield", "Payout", "Payout (12m calc.)", "ROE",
        "Margem Líq.", "Dívida/PL", "Valor de Mercado", "Beta", "Faixa 52 sem.",
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


def _formatar_valor_grande(valor: float | None) -> str:
    """Mesma ideia do 'R$ X bi/mi' já usado pro Valor de Mercado, só que
    aceitando valor negativo (dívida líquida pode ser negativa quando a
    empresa tem mais caixa do que dívida — 'dívida líquida negativa' é a
    forma como o mercado chama isso, não é um erro de conta)."""
    if valor is None:
        return '<span class="texto-apagado">—</span>'
    sinal = "-" if valor < 0 else ""
    absoluto = abs(valor)
    if absoluto >= 1e9:
        return f"{sinal}R$ {absoluto / 1e9:.1f} bi"
    if absoluto >= 1e6:
        return f"{sinal}R$ {absoluto / 1e6:.0f} mi"
    if absoluto >= 1e3:
        return f"{sinal}R$ {absoluto / 1e3:.0f} mil"
    return f"{sinal}R$ {absoluto:.0f}"


def _tabela_indicadores_preco_teto_html(lista_ativos: list[dict], fundamentos: dict[str, dict]) -> None:
    linhas = []
    for a in lista_ativos:
        ticker = a["ticker"]
        f = fundamentos.get(ticker)
        classe_linha = ' class="linha-alvo"' if a["eh_alvo"] else ""
        tipo_html = ' 🎯' if a["eh_alvo"] else ""

        if not f:
            linhas.append(
                f'<tr{classe_linha}><td><span class="ticker">{ticker}{tipo_html}</span></td>'
                f'<td colspan="4"><span class="texto-apagado">— sem fundamentos buscados ainda</span></td></tr>'
            )
            continue

        num_acoes = f.get("num_acoes")
        acoes_html = f"{formatar_numero(num_acoes / 1e6, 1)} mi" if num_acoes else '<span class="texto-apagado">—</span>'
        crescimento = f.get("crescimento_receita")
        crescimento_html = formatar_pct(crescimento * 100) if crescimento is not None else '<span class="texto-apagado">—</span>'
        divida_liquida = f.get("divida_liquida")
        cor_divida = COR_NEUTRO if divida_liquida is None else (COR_POSITIVO if divida_liquida <= 0 else COR_NEGATIVO)

        linhas.append(
            f'<tr{classe_linha}>'
            f'<td><span class="ticker">{ticker}{tipo_html}</span></td>'
            f'<td>{_formatar_valor_grande(f.get("free_cashflow"))}</td>'
            f'<td style="color:{cor_divida}">{_formatar_valor_grande(divida_liquida)}</td>'
            f'<td>{acoes_html}</td>'
            f'<td>{crescimento_html}</td>'
            f'</tr>'
        )

    colunas = ["Ticker", "FCF Livre (12m)", "Dívida Líquida", "Nº de Ações", "Cresc. Receita"]
    tabela_html = f"""
    <div style="overflow-x:auto">
    <table class="tabela-carteira">
        <thead><tr>{''.join(f'<th>{c}</th>' for c in colunas)}</tr></thead>
        <tbody>{''.join(linhas)}</tbody>
    </table>
    </div>
    """
    st.markdown(tabela_html, unsafe_allow_html=True)


def _secao_analise_avancada(dados: dict, salvar, lista_ativos: list[dict], fundamentos: dict[str, dict]) -> None:
    """
    Piotroski F-Score, Altman Z-Score e o "football field" de valuation
    (core/piotroski.py, core/altman.py, core/valuation_multiplos.py) — três
    leituras adicionais além do que já está nas tabelas acima. Separado num
    botão à parte porque Piotroski/Altman exigem buscar as demonstrações
    financeiras ANUAIS completas (bem mais pesado que os fundamentos
    básicos usados no resto da aba).
    """
    st.subheader("🧮 Análise Avançada — Piotroski, Altman e Football Field")
    st.caption(
        "Três leituras adicionais de qualidade e risco financeiro. Piotroski e Altman exigem buscar as "
        "demonstrações financeiras ANUAIS completas (mais pesado que os fundamentos básicos acima) — por "
        "isso ficam num botão separado, que não roda automaticamente."
    )

    if st.button("🔄 Atualizar Análise Avançada (Piotroski/Altman)", use_container_width=True):
        atualizar_analise_avancada(dados, salvar)
        st.rerun()

    exibir_status_analise_avancada()

    if not lista_ativos:
        return

    piotroski_salvo = dados.get("piotroski", {})
    altman_salvo = dados.get("altman", {})
    tickers_disponiveis = [a["ticker"] for a in lista_ativos]

    ticker_selecionado = st.selectbox("Ver análise avançada de:", tickers_disponiveis, key="sel_analise_avancada")
    ativo_selecionado = next(a for a in lista_ativos if a["ticker"] == ticker_selecionado)
    f = fundamentos.get(ticker_selecionado) or {}

    col_piotroski, col_altman = st.columns(2)

    with col_piotroski:
        st.markdown("##### 🧾 Piotroski F-Score")
        resultado_salvo = piotroski_salvo.get(ticker_selecionado)
        if not resultado_salvo:
            st.caption("Ainda não buscado para este ativo — clique em \"Atualizar Análise Avançada\" acima.")
        else:
            pontos = resultado_salvo["pontos"]
            total = resultado_salvo["totalAvaliado"]
            st.metric("Pontuação", f"{pontos}/{total}", resultado_salvo["classificacao"])
            with st.expander("Ver os 9 critérios"):
                for criterio in resultado_salvo.get("criterios", []):
                    if criterio["passou"] is True:
                        icone = "✅"
                    elif criterio["passou"] is False:
                        icone = "❌"
                    else:
                        icone = "➖"
                    st.caption(f"{icone} **{criterio['grupo']}** — {criterio['rotulo']}")

    with col_altman:
        st.markdown("##### ⚠️ Altman Z-Score")
        resultado_salvo_altman = altman_salvo.get(ticker_selecionado)
        if not resultado_salvo_altman:
            st.caption("Ainda não buscado para este ativo — clique em \"Atualizar Análise Avançada\" acima.")
        else:
            z = resultado_salvo_altman["zScore"]
            st.metric("Z-Score", formatar_numero(z, 2) if z is not None else "—", resultado_salvo_altman["classificacao"])
            if (ativo_selecionado.get("setor") or "") == "Bancos":
                st.caption("⚠️ Modelo calibrado para indústria — leitura para bancos costuma não fazer sentido (ver abaixo).")

    st.markdown("##### 🏈 Football Field de Valuation")
    st.caption(
        "Combina o Preço Teto (FCD, já calculado na aba 🎯), o Número de Graham e o Valor Patrimonial por "
        "Ação (a partir do LPA/VPA buscados no Yahoo Finance). Informe um P/L abaixo para incluir também um "
        "valor pelo múltiplo de P/L — sem isso, esse método fica de fora."
    )
    pl_alvo = st.number_input(
        f"P/L que você considera razoável para {ticker_selecionado} (0 = não usar este método)",
        min_value=0.0, step=0.5, value=0.0, key=f"pl_alvo_{ticker_selecionado}",
    )
    resultado_ff = valuation_multiplos.montar_football_field(
        lpa=f.get("lpa"), vpa=f.get("vpa"),
        pl_alvo=pl_alvo if pl_alvo > 0 else None,
        preco_teto_dcf=ativo_selecionado.get("preco_teto"),
    )
    if not resultado_ff.metodos:
        st.caption("Sem dados suficientes ainda — busque os Fundamentos e/ou calcule o Preço Teto (aba 🎯) deste ativo primeiro.")
    else:
        for metodo in resultado_ff.metodos:
            st.write(f"- **{metodo.nome}**: {formatar_moeda(metodo.preco_justo)}")
        st.markdown(
            f"**Faixa: {formatar_moeda(resultado_ff.minimo)} — {formatar_moeda(resultado_ff.maximo)}** "
            f"(média: {formatar_moeda(resultado_ff.media)})"
        )
        cotacao_atual = ativo_selecionado.get("cotacao_atual")
        if cotacao_atual is not None:
            if cotacao_atual < resultado_ff.minimo:
                st.success(f"Cotação atual ({formatar_moeda(cotacao_atual)}) está ABAIXO de toda a faixa.")
            elif cotacao_atual > resultado_ff.maximo:
                st.warning(f"Cotação atual ({formatar_moeda(cotacao_atual)}) está ACIMA de toda a faixa.")
            else:
                st.info(f"Cotação atual ({formatar_moeda(cotacao_atual)}) está DENTRO da faixa.")

    with st.expander("ℹ️ Sobre o Piotroski, o Altman e o Football Field"):
        st.markdown(
            "- **Piotroski F-Score** (0 a 9): mede a saúde financeira comparando o ano fiscal mais recente com "
            "o anterior, em 9 critérios (rentabilidade, alavancagem/liquidez, eficiência operacional). 8-9 = "
            "forte; 0-2 = fraca; o resto é neutro. Quando falta algum dado, aquele critério específico fica de "
            "fora da conta — nunca conta como se a empresa tivesse ido mal.\n"
            "- **Altman Z-Score**: estima o risco de dificuldade financeira grave nos próximos ~2 anos. Z > "
            "2.99 = zona segura; entre 1.81 e 2.99 = zona de alerta; abaixo de 1.81 = zona de risco. ⚠️ O "
            "modelo foi calibrado com empresas industriais dos anos 1960 — bancos e outras financeiras têm "
            "estrutura de balanço tão diferente que a fórmula tende a dar leituras sem sentido para elas.\n"
            "- **Football Field**: o nome vem do gráfico clássico que empilha várias estimativas de 'preço "
            "justo' para comparar a FAIXA entre elas, em vez de confiar num único método. Nenhum método é 'o "
            "certo' — quanto mais métodos concordarem numa faixa parecida, mais confiança a estimativa costuma "
            "merecer.\n"
            "- Assim como os outros indicadores desta aba, tudo aqui é uma estimativa para ajudar a pensar — "
            "não é recomendação de compra ou venda."
        )
