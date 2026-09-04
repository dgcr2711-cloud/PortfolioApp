"""
Monta o "retrato" (snapshot) resumido e já calculado da carteira que é
enviado para o Firestore e consumido pelo app do celular — ver
core/cloud_sync.py.

Ideia central: o celular NUNCA recalcula preço médio, preço teto, HHI de
concentração etc. do zero — ele só lê o resultado que este arquivo monta a
partir das mesmíssimas funções de core/calculations.py e
core/portfolio_analytics.py já usadas (e testadas) na tela do PC. Isso
evita duplicar fórmulas financeiras em duas linguagens/plataformas
diferentes, que é a forma mais comum de dois apps "desencontrarem" os
números com o tempo.

2026-09-04: adicionado "historicoPrecosAtivos" — histórico diário de
fechamento por ativo (mesma fonte/cache do "Gráfico do Ativo" da aba
Carteira do PC), pra alimentar o gráfico equivalente na aba Preço Teto do
celular (ver _montar_historico_precos_ativos abaixo).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core import calculations as calc
from core import imposto_renda as ir_calc
from core import market_data
from core import portfolio_analytics as analytics
from core import rebalanceamento as rebal_calc
from core import risco as risco_calc
from core import valuation_multiplos
from ui.ativos import montar_lista_ativos


def _montar_fundamentos_ativo(f: dict[str, Any] | None) -> dict[str, Any] | None:
    """Achata os fundamentos de UM ativo (mesmos campos da tabela "Indicadores por
    Ativo" da aba 🔎 Fundamentos do PC) para o formato que o celular consome.
    Retorna None quando o ativo ainda não teve fundamentos buscados — o celular
    trata isso mostrando "sem fundamentos buscados ainda", igual ao PC."""
    if not f:
        return None
    return {
        "setorYahoo": f.get("setor_yahoo"),
        "pl": f.get("pl"),
        "plProjetado": f.get("pl_projetado"),
        "pvp": f.get("pvp"),
        "lpa": f.get("lpa"),
        "vpa": f.get("vpa"),
        "dividendYield": f.get("dividend_yield"),
        "payoutRatio": f.get("payout_ratio"),
        "payoutTtmCalculado": f.get("payout_ttm_calculado"),
        "roe": f.get("roe"),
        "margemLiquida": f.get("margem_liquida"),
        "dividaPatrimonio": f.get("divida_patrimonio"),
        "valorMercado": f.get("valor_mercado"),
        # Mesmos indicadores da tabela "🎯 Indicadores para o Preço Teto" do PC.
        "freeCashflow": f.get("free_cashflow"),
        "dividaLiquida": f.get("divida_liquida"),
        "numAcoes": f.get("num_acoes"),
        "crescimentoReceita": f.get("crescimento_receita"),
        "beta": f.get("beta"),
        "minima52s": f.get("minima_52s"),
        "maxima52s": f.get("maxima_52s"),
    }


def _montar_piotroski_ativo(p: dict[str, Any] | None) -> dict[str, Any] | None:
    """Achata o resultado do Piotroski F-Score (core/piotroski.py, salvo por
    ui.acoes_comuns.atualizar_analise_avancada) para o formato do celular.
    None quando o ativo ainda não teve a análise avançada buscada."""
    if not p:
        return None
    return {
        "pontos": p.get("pontos"),
        "totalAvaliado": p.get("totalAvaliado"),
        "classificacao": p.get("classificacao"),
        "criterios": [
            {"chave": c.get("chave"), "rotulo": c.get("rotulo"), "grupo": c.get("grupo"), "passou": c.get("passou")}
            for c in (p.get("criterios") or [])
        ],
    }


def _montar_altman_ativo(a: dict[str, Any] | None) -> dict[str, Any] | None:
    """Achata o resultado do Altman Z-Score (core/altman.py)."""
    if not a:
        return None
    return {"zScore": a.get("zScore"), "classificacao": a.get("classificacao")}


def _montar_football_field_ativo(f: dict[str, Any] | None, preco_teto: float | None) -> dict[str, Any] | None:
    """
    Football field (core/valuation_multiplos.py) com os métodos que NÃO
    dependem de uma escolha manual de sessão: FCD (o preço-teto já salvo),
    Número de Graham e Valor Patrimonial por Ação. O método "Múltiplo de
    P/L-alvo" fica de fora do celular de propósito — ele depende de um
    multiplicador que o usuário escolhe na hora, na aba Fundamentos do PC
    (é uma exploração "e se?", não um dado salvo na carteira), então não
    haveria um valor único e estável para mandar pro celular.
    """
    lpa = (f or {}).get("lpa")
    vpa = (f or {}).get("vpa")
    resultado = valuation_multiplos.montar_football_field(lpa=lpa, vpa=vpa, pl_alvo=None, preco_teto_dcf=preco_teto)
    if not resultado.metodos:
        return None
    return {
        "metodos": [{"nome": m.nome, "precoJusto": m.preco_justo} for m in resultado.metodos],
        "minimo": resultado.minimo,
        "maximo": resultado.maximo,
        "media": resultado.media,
    }


def _montar_historico_patrimonio(historico: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mesmos pontos usados no gráfico "Patrimônio ao longo do tempo" da aba 📊 Evolução do PC."""
    return [
        {
            "data": h["data"],
            "totalInvestido": h["totalInvestido"],
            "totalAtual": h["totalAtual"],
            "ibov": h.get("ibov"),
        }
        for h in historico
    ]


def _montar_twr_vs_ibovespa(twr: dict[str, Any] | None) -> dict[str, Any] | None:
    if not twr:
        return None
    return {
        "rentCarteiraPct": twr["rent_carteira_pct"],
        "rentIbovPct": twr["rent_ibov_pct"],
        "dataInicio": twr["data_inicio"],
        "dataFim": twr["data_fim"],
    }


def _montar_risco(historico: list[dict[str, Any]], taxa_livre_risco_anual_pct: float) -> dict[str, Any]:
    """Mesmo cálculo de Beta/Sharpe da seção "📐 Risco da Carteira" da aba
    Evolução do PC (core/risco.py) — a taxa livre de risco é a que o usuário
    configurou por lá (dados['taxaLivreRiscoAnualPct'])."""
    resultado = risco_calc.calcular_risco_carteira(historico, taxa_livre_risco_anual_pct)
    return {
        "beta": resultado.beta,
        "sharpeAnualizado": resultado.sharpe_anualizado,
        "numeroPeriodos": resultado.numero_periodos,
        "diasCobertos": resultado.dias_cobertos,
        "aviso": resultado.aviso,
        "taxaLivreRiscoAnualPctUsada": taxa_livre_risco_anual_pct,
    }


def _montar_rebalanceamento(posicoes: list[dict[str, Any]], metas_pct: dict[str, float]) -> dict[str, Any]:
    """Mesmos desvios da seção "🎯 Metas de Alocação & Rebalanceamento" da
    aba Carteira do PC (core/rebalanceamento.py) — o celular só EXIBE; quem
    define as metas continua sendo o PC (ui/carteira.py)."""
    desvios = rebal_calc.calcular_desvios(posicoes, metas_pct)
    return {
        "temMetas": bool(metas_pct),
        "desvios": [
            {
                "ticker": d.ticker,
                "metaPct": d.meta_pct,
                "atualPct": d.atual_pct,
                "desvioPp": d.desvio_pp,
                "valorAtual": d.valor_atual,
                "valorAlvo": d.valor_alvo,
                "valorAjuste": d.valor_ajuste,
                "alerta": d.alerta,
            }
            for d in desvios
        ],
    }


def _montar_proventos(proventos: list[dict[str, Any]], total_investido_atual: float) -> dict[str, Any]:
    """Lista completa (pro histórico da aba Proventos do celular) + o mesmo resumo
    (total geral, 12 meses, Yield on Cost) calculado pela aba 📅 Proventos do PC."""
    resumo = calc.resumo_proventos(proventos, total_investido_atual)
    lista = sorted(
        [
            {"id": p["id"], "ticker": p["ticker"], "data": p["data"], "tipo": p["tipo"], "valor": p["valor"]}
            for p in proventos
        ],
        key=lambda p: p["data"],
        reverse=True,
    )
    return {
        "resumo": {
            "totalGeral": resumo["total_geral"],
            "total12m": resumo["total_12m"],
            "yieldOnCost": resumo["yield_on_cost"],
        },
        "lista": lista,
    }


def _montar_precos_teto(precos_teto: dict[str, Any]) -> list[dict[str, Any]]:
    """Achata o dict ticker -> {...} salvo pela calculadora FCD (ui/preco_teto.py) numa lista, mais fácil de listar em React Native."""
    return [
        {
            "ticker": ticker,
            "precoTeto": v["precoTeto"],
            "precoTetoComMargem": v["precoTetoComMargem"],
            "atualizadoEm": v.get("atualizadoEm"),
        }
        for ticker, v in sorted(precos_teto.items())
    ]


def _montar_teses(teses_por_ticker: dict[str, Any]) -> dict[str, Any]:
    """Achata o diário de tese (core/teses.py) — ticker -> lista de entradas, mais recente primeiro."""
    return {
        ticker: [
            {"id": e["id"], "data": e["data"], "texto": e["texto"]}
            for e in sorted(entradas, key=lambda e: e["data"], reverse=True)
        ]
        for ticker, entradas in teses_por_ticker.items()
        if entradas
    }


def _montar_historico_transacoes(compras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Espelha a tabela "Histórico de Transações" da aba 🧾 Compras & Vendas do PC —
    inclui o "id" de cada transação, necessário pro celular pedir a remoção de uma
    específica (core/pendencias_celular.py -> aplicar_remocoes_do_celular)."""
    ordenadas = sorted(compras, key=lambda c: c["data"], reverse=True)
    return [
        {
            "id": c["id"],
            "tipo": c.get("tipo", "compra"),
            "ticker": c["ticker"],
            "data": c["data"],
            "qtd": c["qtd"],
            "preco": c["preco"],
            "taxas": c.get("taxas") or 0,
        }
        for c in ordenadas
    ]


def _montar_imposto_renda(dados: dict[str, Any]) -> dict[str, Any]:
    """Mesmos cálculos da aba 🏛️ Imposto de Renda do PC (core/imposto_renda.py):
    resumo mensal (Swing x Day Trade já compensando prejuízo e descontando
    IRRF), posição em 31/12 de cada ano JÁ FECHADO (pra ficha "Bens e
    Direitos" da declaração anual — não faz sentido mostrar o ano corrente,
    que ainda não fechou) e total de proventos por ano (pra "Rendimentos
    Isentos"/"Tributação Exclusiva"). Tudo pré-calculado aqui, igual ao
    resto do snapshot — o celular só formata e mostra, sem duplicar a
    fórmula em TypeScript."""
    compras = dados["compras"]
    eventos = dados["eventos"]
    proventos = dados.get("proventos") or []

    resultado = ir_calc.construir_resultados_ir(compras, eventos)
    resumo_mensal = [
        {
            "mes": r["mes"],
            "swingVendido": r["swing"]["total_vendido"],
            "swingLucro": r["swing"]["lucro"],
            "swingIsento": r["swing"]["isento"],
            "swingImposto": r["swing"]["imposto"],
            "swingIrrf": r["swing"]["irrf_estimado"],
            "dayTradeLucro": r["day_trade"]["lucro"],
            "dayTradeImposto": r["day_trade"]["imposto"],
            "dayTradeIrrf": r["day_trade"]["irrf_estimado"],
            "impostoDevidoMes": r["imposto_devido_mes"],
            "darfAPagar": r["darf_a_pagar"],
            "abaixoDoMinimo": r["abaixo_do_minimo"],
        }
        for r in ir_calc.resumo_mensal_ir(resultado)
    ]

    ano_atual = datetime.now().year
    anos_com_compras = sorted({(c.get("data") or "")[:4] for c in compras if c.get("data")})
    anos_fechados = [a for a in anos_com_compras if a and int(a) < ano_atual]
    bens_e_direitos = []
    for ano in anos_fechados:
        data_corte = f"{ano}-12-31"
        posicoes = ir_calc.posicoes_em_data(compras, eventos, data_corte)
        if not posicoes:
            continue
        bens_e_direitos.append({
            "ano": ano,
            "dataCorte": data_corte,
            "posicoes": [
                {
                    "ticker": p["ticker"], "qtdTotal": p["qtd_total"],
                    "valorTotalInvestido": p["valor_total_investido"],
                    "precoMedioPonderado": p["preco_medio_ponderado"],
                }
                for p in sorted(posicoes, key=lambda p: p["ticker"])
            ],
            "totalInvestido": sum(p["valor_total_investido"] for p in posicoes),
        })

    anos_proventos = sorted({(p.get("data") or "")[:4] for p in proventos if p.get("data")}, reverse=True)
    proventos_por_ano = []
    for ano in anos_proventos:
        r = ir_calc.resumo_anual_proventos(proventos, ano)
        proventos_por_ano.append({
            "ano": ano,
            "dividendos": r["dividendos"],
            "jcp": r["jcp"],
            "rendimentosFii": r["rendimentos_fii"],
            "jcpIrrfEstimado": r["jcp_irrf_estimado"],
        })

    return {
        "resumoMensal": resumo_mensal,
        "bensEDireitos": bens_e_direitos,
        "proventosPorAno": proventos_por_ano,
        "avisos": resultado.avisos,
    }


def _montar_historico_precos_ativos(lista_ativos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    2026-09-04 (Diego pediu pra ver, na aba Preço Teto do celular, "o
    gráfico que temos no site em carteira"): histórico diário de
    fechamento por ativo, mesmo período padrão (6 meses) do "Gráfico do
    Ativo" da aba Carteira do PC — usa a MESMA função e cache de
    `ui/carteira.py::_secao_grafico_individual`
    (`core.market_data.buscar_historico_preco`, cache de 1h — ver
    CACHE_TTL_HISTORICO_PRECO_SEGUNDOS em core/config.py), então
    sincronizar algumas vezes seguidas não bate no Yahoo Finance de novo à
    toa. Ativos sem histórico disponível (falha de rede pontual, ticker
    não encontrado) simplesmente não entram na lista — o celular trata
    como "sem gráfico disponível para este ativo".
    """
    resultado = []
    for ativo in lista_ativos:
        pontos = market_data.buscar_historico_preco(ativo["ticker"], "6mo")
        if pontos:
            resultado.append({"ticker": ativo["ticker"], "pontos": pontos})
    return resultado


def montar_snapshot_para_celular(dados: dict[str, Any]) -> dict[str, Any]:
    """Retorna um dicionário "achatado" (fácil de ler em JS/TypeScript), pronto para core.cloud_sync.sincronizar_snapshot()."""
    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    totais = calc.totais_carteira(posicoes)
    proventos_12m = calc.proventos_12m(dados["proventos"])
    lista_ativos = montar_lista_ativos(dados)

    concentracao = analytics.concentracao_por_ativo(posicoes)
    diag = analytics.diagnostico_concentracao(concentracao)
    diversificacao = analytics.diversificacao_setorial(posicoes, dados.get("setores", {}))
    cagr = analytics.cagr_aproximado(dados.get("historico", []))
    drawdown = analytics.maior_perda_registrada(dados.get("historico", []))
    fundamentos_pond = analytics.fundamentos_ponderados(posicoes, dados.get("fundamentos", {}))
    fundamentos_brutos = dados.get("fundamentos", {})
    total_investido_atual = sum(p["valor_total_investido"] for p in posicoes)

    return {
        "atualizadoEm": datetime.now().isoformat(),
        "totais": {
            "totalAtual": totais["total_atual"],
            "totalInvestido": totais["total_investido"],
            "lucro": totais["lucro"],
            "rentabilidadePct": totais["rentabilidade_pct"],
            "variacaoDiaReais": totais["variacao_dia_reais"],
            "proventos12m": proventos_12m,
        },
        "ativos": [
            {
                "ticker": a["ticker"],
                "ehAlvo": a["eh_alvo"],
                "setor": a.get("setor"),
                "qtdTotal": a["qtd_total"],
                "precoMedio": a["preco_medio_ponderado"],
                "cotacaoAtual": a["cotacao_atual"],
                "atual": a["atual"],
                "lucroReais": a["lucro_reais"],
                "lucroPct": a["lucro_pct"],
                "variacaoDiaPct": a["variacao_dia_pct"],
                "precoTeto": a["preco_teto"],
                "indicacao": a["indicacao"],
                "fundamentos": _montar_fundamentos_ativo(fundamentos_brutos.get(a["ticker"])),
                "piotroski": _montar_piotroski_ativo(dados.get("piotroski", {}).get(a["ticker"])),
                "altman": _montar_altman_ativo(dados.get("altman", {}).get(a["ticker"])),
                "footballField": _montar_football_field_ativo(fundamentos_brutos.get(a["ticker"]), a["preco_teto"]),
            }
            for a in lista_ativos
        ],
        "diagnostico": {
            "maiorTicker": diag.maior_ticker,
            "maiorPesoPct": diag.maior_peso_pct,
            "indiceHhi": diag.indice_hhi,
            "classificacaoHhi": diag.classificacao_hhi,
            "alertaConcentracao": diag.alerta_concentracao,
            "setores": diversificacao,
            "cagrAproximado": cagr,
            "maiorPerdaRegistrada": drawdown,
            "fundamentosPonderados": fundamentos_pond,
        },
        "historico": _montar_historico_patrimonio(dados.get("historico", [])),
        "twrVsIbovespa": _montar_twr_vs_ibovespa(calc.twr_vs_ibovespa(dados.get("historico", []))),
        "risco": _montar_risco(dados.get("historico", []), dados.get("taxaLivreRiscoAnualPct", 10.0)),
        "rebalanceamento": _montar_rebalanceamento(posicoes, dados.get("metasAlocacao", {})),
        "proventos": _montar_proventos(dados["proventos"], total_investido_atual),
        "precosTeto": _montar_precos_teto(dados.get("precosTeto", {})),
        "historicoPrecosAtivos": _montar_historico_precos_ativos(lista_ativos),
        "compras": _montar_historico_transacoes(dados["compras"]),
        "impostoRenda": _montar_imposto_renda(dados),
        "teses": _montar_teses(dados.get("teses", {})),
    }
