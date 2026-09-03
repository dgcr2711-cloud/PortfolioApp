"""
Aba "🏠 Visão Geral" — resumo de todos os recursos numa tela só: os 5 cards
de KPI, os 2 gráficos (Alocação + Evolução Patrimonial) e a tabela
compacta com posições + empresas-alvo do dashboard original.

2026-09-03 (refinamento estético, pedido do Diego — "estética minimalista,
divulgação progressiva"): o Painel de Diagnóstico e a tabela completa de
ativos — os dois blocos mais densos da tela — passaram a viver dentro de
`st.expander`, recolhidos por padrão. Cards + gráficos continuam sempre
visíveis (é o "essencial de bater o olho"); o resto fica a um clique de
distância, sem sumir de vez.
"""

from __future__ import annotations

import streamlit as st

from core import calculations as calc
from core import portfolio_analytics as analytics
from core.config import COR_DESTAQUE, COR_NEGATIVO, COR_NEUTRO, COR_POSITIVO
from core.formatting import formatar_moeda_priv, formatar_numero, formatar_pct
from ui.ativos import montar_lista_ativos
from ui.graficos import grafico_alocacao, grafico_evolucao_patrimonial
from ui.styles import (
    aviso_privacidade_html,
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

    _exibir_taxas_economicas(dados.get("taxasEconomicas"))

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

    cor_lucro = "#34d399" if totais["lucro"] >= 0 else "#F87171"
    sinal = "+" if totais["lucro"] >= 0 else ""

    # Os cards "Patrimônio Atual" e "Resultado" abaixo já refletem
    # automaticamente qualquer cotação vinda da HG Brasil (2026-09-03):
    # `totais` vem de `posicoes`, calculado a partir de dados["cotacoes"] —
    # o mesmo dicionário onde ui/acoes_comuns.py::atualizar_dados() grava
    # tanto os preços do Yahoo Finance quanto os da HG Brasil (usada como
    # plano B). Não existe uma cotação "HG Brasil" separada para ler aqui;
    # é a mesma fonte de sempre, só com mais uma origem possível por trás.
    # Divulgação progressiva também dentro da própria linha de KPIs
    # (2026-09-03, pedido do Diego): os 3 números essenciais — Patrimônio,
    # Resultado (R$ e %) e Proventos — ficam em destaque, tamanho normal;
    # os 2 secundários (contagens de alertas/ativos, que não são um valor
    # financeiro em si) ficam numa segunda linha menor, ainda sempre
    # visíveis (não é preciso abrir nada pra vê-los), só sem competir
    # visualmente com o que mais importa.
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
    ])
    render_cards([
        card_kpi_html("Alertas Atingidos", f"{atingidos} / {len(alertas)}", compacto=True),
        card_kpi_html("Ativos Monitorados", f"{n_carteira} na carteira + {n_alvo} alvo(s)", compacto=True),
    ])

    _render_graficos_resumo(dados, posicoes, ocultar_valores)

    # Os dois blocos mais densos da tela — diagnóstico avançado e a tabela
    # completa de ativos — ficam recolhidos por padrão (2026-09-03,
    # "divulgação progressiva"): quem só quer bater o olho no patrimônio e
    # nos gráficos não precisa rolar a tela toda pra chegar lá embaixo, mas
    # nada foi removido — é só um clique de distância.
    if posicoes:
        with st.expander("🏛️ Diagnóstico da Carteira (concentração, setores, CAGR, fundamentos)"):
            _render_diagnostico_carteira(dados, posicoes)

    with st.expander(f"📋 Todos os ativos — posições + alvo ({len(lista_ativos)})"):
        _render_tabela_ativos(lista_ativos)


def _render_tabela_ativos(lista_ativos: list[dict]) -> None:
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
    <div class="card-tabela">
    <table class="tabela-carteira">
        <thead><tr><th>Ticker</th><th>Tipo</th><th>Cotação</th><th>Alerta</th><th>Preço Teto</th><th>Preço Teto c/ Margem (20%)</th><th>Indicação</th></tr></thead>
        <tbody>{''.join(linhas_html)}</tbody>
    </table>
    </div>
    """
    st.markdown(tabela_html, unsafe_allow_html=True)


def _agrupar_para_donut(posicoes_com_valor: list[dict], limite: int = 7) -> tuple[list[str], list[float]]:
    """
    Agrupa o excedente em "Outros" quando há mais posições do que cores
    validadas na paleta do donut (2026-09-03, pesquisa do skill interno de
    dataviz — ver `ui/graficos.py::PALETA_ALOCACAO`): uma 8ª/9ª cor
    "inventada" deixaria de ser a ordem validada contra daltonismo —
    melhor juntar as menores posições num "Outros" do que reciclar cor.
    Mantém as `limite - 1` maiores posições e soma o resto num "Outros";
    ordena por valor decrescente antes de cortar, pra "Outros" ser sempre
    o conjunto das MENORES posições, nunca uma escolha arbitrária. Com
    `limite` posições ou menos (o caso normal do Diego hoje — 6 ativos),
    não muda nada.
    """
    ordenadas = sorted(posicoes_com_valor, key=lambda p: p["atual"], reverse=True)
    if len(ordenadas) <= limite:
        return [p["ticker"] for p in ordenadas], [p["atual"] for p in ordenadas]
    principais, resto = ordenadas[: limite - 1], ordenadas[limite - 1 :]
    labels = [p["ticker"] for p in principais] + ["Outros"]
    valores = [p["atual"] for p in principais] + [sum(p["atual"] for p in resto)]
    return labels, valores


def _render_graficos_resumo(dados: dict, posicoes: list[dict], ocultar_valores: bool) -> None:
    """
    Os dois gráficos que faltavam na Visão Geral (pedido do Diego,
    2026-09-03): alocação (donut, igual ao de 📈 Carteira) e evolução
    patrimonial (igual ao de 📊 Evolução) lado a lado, em versão compacta —
    aqui é só o resumo rápido; os detalhes (agrupar por setor, comparar com
    o Ibovespa, Beta/Sharpe) continuam nas abas específicas.

    Privacidade ("ocultar valores", 2026-09-03, pedido do Diego): o donut
    de Alocação em si já mostra só Ticker + percentual (nunca um valor em
    R$) — o total no centro (novo, mesmo refinamento visual) usa
    `formatar_moeda_priv`, então já sai mascarado ("R$ ••••") sozinho
    quando `ocultar_valores` está ativo, sem precisar de nenhum tratamento
    especial aqui. Já a Evolução Patrimonial é uma série histórica em R$ —
    mascarar só os números com "••••" não bastaria, porque a FORMA da
    curva ainda revelaria a trajetória do patrimônio. Por isso, com
    `ocultar_valores` ativo, o gráfico inteiro é substituído por um aviso
    — a informação some de verdade, não só fica mascarada.
    """
    col_alocacao, col_evolucao = st.columns(2)

    with col_alocacao:
        st.subheader("Alocação")
        posicoes_com_valor = [p for p in posicoes if p["atual"] > 0]
        with st.container(border=True):
            if not posicoes_com_valor:
                st.caption("Sem posições para exibir no gráfico ainda.")
            else:
                labels_donut, valores_donut = _agrupar_para_donut(posicoes_com_valor)
                fig = grafico_alocacao(
                    labels_donut, valores_donut,
                    altura=300,
                    valor_central=formatar_moeda_priv(sum(valores_donut), ocultar_valores),
                    rotulo_central="Patrimônio",
                    # 2026-09-03: o R$ por fatia (rótulo de fora do donut) foi
                    # tentado numa rodada anterior por pesquisa de dashboards
                    # de investimento, mas Diego viu ao vivo e achou
                    # desnecessário/poluído — o total em R$ já aparece bem no
                    # centro da rosca, então as fatias voltam a mostrar só
                    # "TICKER - XX,X%" (comportamento de antes desta rodada).
                    # `valores_formatados` continua existindo em
                    # `grafico_alocacao` caso outra tela queira usá-lo.
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_evolucao:
        st.subheader("Evolução Patrimonial")
        historico = dados.get("historico", [])
        with st.container(border=True):
            if ocultar_valores:
                st.markdown(
                    aviso_privacidade_html("Evolução patrimonial oculta — desative \"ocultar valores\" para visualizar."),
                    unsafe_allow_html=True,
                )
            elif not historico:
                st.caption("Ainda não há snapshots suficientes — atualize as cotações em dias diferentes para ver a evolução aqui.")
            else:
                fig = grafico_evolucao_patrimonial(historico, altura=260, legenda=False)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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


def _exibir_taxas_economicas(taxas: dict | None) -> None:
    """
    Linha compacta com a SELIC e o CDI mais recentes (HG Brasil,
    2026-09-03) — fica logo abaixo do título, sem ocupar um card inteiro na
    grade (mesma lógica de otimização de espaço já aplicada ao resto da
    tela). Não mostra nada se a chave da HG Brasil ainda não foi
    configurada (taxas vazio) — não é um recurso obrigatório.
    """
    if not taxas:
        return
    partes = []
    if taxas.get("selic") is not None:
        partes.append(f"Selic: {formatar_pct(taxas['selic'])}")
    if taxas.get("cdi") is not None:
        partes.append(f"CDI: {formatar_pct(taxas['cdi'])}")
    if not partes:
        return
    data_taxa = taxas.get("data") or ""
    st.caption(f"📈 {' • '.join(partes)}" + (f" (referência: {data_taxa})" if data_taxa else "") + " — HG Brasil Finance")
