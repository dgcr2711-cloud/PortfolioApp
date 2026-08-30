"""
Toda a lógica de cálculo da carteira, portada 1:1 da versão em JavaScript
do dashboard original (mesmas fórmulas e mesmos critérios), para que os
números batam exatamente com o que você já via no HTML.

Este módulo é "puro": não lê arquivo, não chama a internet, não usa
Streamlit. Ele só recebe dicionários/listas (do core.data_store) e devolve
números e listas prontos para exibir. Isso facilita testar e depurar —
e se um dia você quiser adicionar um teste automatizado, é só chamar essas
funções com dados de exemplo, sem precisar rodar o app inteiro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from core.config import (
    MARGEM_SEGURANCA_PADRAO,
    regra_ir_vigente_em,
)


# ==========================================================================
# Ledger: consolida compras + vendas + eventos societários numa posição por
# ativo, na ordem cronológica em que aconteceram (igual a construirLedger()
# no JS original).
# ==========================================================================

@dataclass
class ResultadoLedger:
    posicoes: dict[str, dict[str, float]] = field(default_factory=dict)   # ticker -> {qtd, custo_total}
    resultados_realizados: list[dict[str, Any]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def construir_ledger(compras: list[dict], eventos: list[dict]) -> ResultadoLedger:
    """
    Percorre compras, vendas e eventos societários em ordem de data e
    calcula, para cada ativo, a quantidade e o custo total acumulados.

    Regras (iguais ao dashboard original):
    - Compra: soma quantidade e custo (qtd*preco + taxas).
    - Venda: baixa pelo PREÇO MÉDIO na data da venda (não pelo preço de
      compra específico) e registra o lucro/prejuízo realizado.
    - Evento societário (desdobramento/grupamento/bonificação): multiplica
      a quantidade pelo fator informado; o custo total NÃO muda, então o
      preço médio se ajusta sozinho.
    """
    posicoes: dict[str, dict[str, float]] = {}
    resultados_realizados: list[dict[str, Any]] = []
    avisos: list[str] = []

    linhas: list[dict[str, Any]] = []
    for c in compras:
        linhas.append({**c, "origem": "transacao", "tipoMov": c.get("tipo", "compra")})
    for ev in eventos:
        linhas.append({**ev, "origem": "evento"})

    # Ordena por data e, em empate, por id — determinístico, igual ao original.
    linhas.sort(key=lambda item: (item.get("data") or "", str(item.get("id", ""))))

    for item in linhas:
        ticker = item.get("ticker")
        if not ticker:
            continue
        pos = posicoes.setdefault(ticker, {"qtd": 0.0, "custo_total": 0.0})

        if item["origem"] == "evento":
            fator = float(item.get("fator") or 1)
            pos["qtd"] = pos["qtd"] * fator
            continue

        qtd = float(item.get("qtd") or 0)
        preco = float(item.get("preco") or 0)
        taxas = float(item.get("taxas") or 0)

        if item["tipoMov"] == "venda":
            preco_medio_na_data = (pos["custo_total"] / pos["qtd"]) if pos["qtd"] > 0 else 0.0
            qtd_vendida = qtd
            if qtd_vendida > pos["qtd"] + 1e-6:
                avisos.append(
                    f"Venda de {qtd} {ticker} em {item.get('data')} é maior que a posição "
                    f"disponível na data ({pos['qtd']:.2f}). Considerando apenas "
                    f"{pos['qtd']:.2f} para não gerar posição negativa."
                )
                qtd_vendida = pos["qtd"]
            custo_base = preco_medio_na_data * qtd_vendida
            receita = (qtd_vendida * preco) - taxas
            lucro = receita - custo_base
            resultados_realizados.append({
                "id": item.get("id"), "ticker": ticker, "data": item.get("data"),
                "qtd": qtd_vendida, "preco_venda": preco, "custo_base": custo_base, "lucro": lucro,
            })
            pos["qtd"] -= qtd_vendida
            pos["custo_total"] -= custo_base
        else:
            custo = (qtd * preco) + taxas
            pos["qtd"] += qtd
            pos["custo_total"] += custo

    return ResultadoLedger(posicoes=posicoes, resultados_realizados=resultados_realizados, avisos=avisos)


def consolidar_posicoes(compras: list[dict], eventos: list[dict]) -> list[dict[str, Any]]:
    """Posição líquida atual por ativo, com preço médio ponderado."""
    ledger = construir_ledger(compras, eventos)
    lista = []
    for ticker, v in ledger.posicoes.items():
        if v["qtd"] > 1e-6:
            lista.append({
                "ticker": ticker,
                "qtd_total": v["qtd"],
                "valor_total_investido": v["custo_total"],
                "preco_medio_ponderado": v["custo_total"] / v["qtd"],
            })
    return lista


def calcular_posicoes_completas(
    compras: list[dict], eventos: list[dict], cotacoes: dict[str, dict]
) -> list[dict[str, Any]]:
    """
    Mesmas posições de consolidar_posicoes(), acrescentando cotação atual,
    valor de mercado, resultado (R$ e %) e variação do dia — para exibir
    direto na tabela da Carteira.
    """
    posicoes = consolidar_posicoes(compras, eventos)
    completas = []
    for p in posicoes:
        cot = cotacoes.get(p["ticker"])
        cotacao_atual = cot["preco"] if cot else p["preco_medio_ponderado"]
        atual = p["qtd_total"] * cotacao_atual
        lucro_reais = atual - p["valor_total_investido"]
        lucro_pct = (lucro_reais / p["valor_total_investido"] * 100) if p["valor_total_investido"] > 0 else 0.0

        variacao_dia_pct = None
        variacao_dia_reais = None
        if cot and cot.get("previousClose"):
            prev = cot["previousClose"]
            variacao_dia_pct = ((cotacao_atual - prev) / prev) * 100
            variacao_dia_reais = (cotacao_atual - prev) * p["qtd_total"]

        completas.append({
            **p,
            "cotacao": cot,
            "cotacao_atual": cotacao_atual,
            "atual": atual,
            "lucro_reais": lucro_reais,
            "lucro_pct": lucro_pct,
            "variacao_dia_pct": variacao_dia_pct,
            "variacao_dia_reais": variacao_dia_reais,
        })
    return completas


# ==========================================================================
# Preço Teto / Margem de Segurança / Indicação (Compra, Neutro, Venda)
# ==========================================================================

def preco_com_margem(preco_teto: float, margem: float = MARGEM_SEGURANCA_PADRAO) -> float:
    """Preço Teto com margem de segurança aplicada (padrão: 20%)."""
    return preco_teto * (1 - margem)


def indicacao(preco_teto: float | None, cotacao_atual: float | None) -> str | None:
    """
    Retorna "compra", "neutro" ou "venda" comparando a cotação atual ao
    Preço Teto (com e sem margem de segurança). None quando falta preço
    teto OU cotação (o chamador decide como exibir cada caso — a mensagem
    correta depende de qual dos dois está faltando).
    """
    if not preco_teto:
        return None
    if cotacao_atual is None:
        return None
    limite_margem = preco_com_margem(preco_teto)
    if cotacao_atual <= limite_margem:
        return "compra"
    if cotacao_atual <= preco_teto:
        return "neutro"
    return "venda"


def margem_vs_preco_medio(preco_teto: float | None, preco_medio: float) -> float | None:
    """Margem do Preço Teto em relação ao preço médio pago (não à cotação atual)."""
    if not preco_teto:
        return None
    return ((preco_teto - preco_medio) / preco_teto) * 100


# ==========================================================================
# Resultado Realizado (vendas) e resumo mensal para IR
# ==========================================================================

def resumo_ir_mensal(resultados_realizados: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Agrupa vendas por mês (AAAA-MM) e estima o IR devido, usando a mesma
    regra simplificada do dashboard original: vendas de ações comuns no
    mercado à vista até o limite de isenção do mês são isentas; acima
    disso, a alíquota do mês sobre o lucro do mês. A alíquota e o limite
    são buscados em core.config.TABELA_IR_ACOES pela data de cada mês, para
    que vendas antigas continuem usando a regra que valia na época, mesmo
    que a Receita mude esses valores no futuro. Não considera day trade,
    FIIs, nem prejuízo compensado de meses anteriores — é só uma estimativa
    rápida, sempre confirme com um contador.
    """
    por_mes: dict[str, dict[str, float]] = {}
    for r in resultados_realizados:
        mes = (r.get("data") or "")[:7]
        if not mes:
            continue
        m = por_mes.setdefault(mes, {"total_vendido": 0.0, "lucro": 0.0})
        m["total_vendido"] += r["qtd"] * r["preco_venda"]
        m["lucro"] += r["lucro"]

    linhas = []
    for mes in sorted(por_mes.keys(), reverse=True):
        m = por_mes[mes]
        regra = regra_ir_vigente_em(mes)
        isento = m["total_vendido"] <= regra["limite_isencao_mensal"]
        imposto_estimado = m["lucro"] * regra["aliquota"] if (not isento and m["lucro"] > 0) else 0.0
        linhas.append({
            "mes": mes, "total_vendido": m["total_vendido"], "lucro": m["lucro"],
            "isento": isento, "imposto_estimado": imposto_estimado,
        })
    return linhas


# ==========================================================================
# Proventos: Yield on Cost
# ==========================================================================

def resumo_proventos(proventos: list[dict], total_investido_atual: float) -> dict[str, float]:
    """Total recebido (histórico), total nos últimos 12 meses e Yield on Cost (12m)."""
    total_geral = sum(p["valor"] for p in proventos)
    um_ano_atras = date.today() - timedelta(days=365)
    total_12m = sum(
        p["valor"] for p in proventos
        if p.get("data") and date.fromisoformat(p["data"][:10]) >= um_ano_atras
    )
    yoc = (total_12m / total_investido_atual * 100) if total_investido_atual > 0 else 0.0
    return {"total_geral": total_geral, "total_12m": total_12m, "yield_on_cost": yoc}


def proventos_12m(proventos: list[dict]) -> float:
    """Usado no card 'Proventos (12m)' da Visão Geral."""
    um_ano_atras = date.today() - timedelta(days=365)
    return sum(
        p["valor"] for p in proventos
        if p.get("data") and date.fromisoformat(p["data"][:10]) >= um_ano_atras
    )


# ==========================================================================
# Evolução patrimonial: comparação com o Ibovespa (TWR aproximado)
# ==========================================================================

def twr_vs_ibovespa(historico: list[dict]) -> dict[str, Any] | None:
    """
    Retorno da carteira "encadeado" por sub-período (aproximação de Time
    Weighted Return), comparado ao retorno simples do Ibovespa no mesmo
    período. A variação do total investido entre dois snapshots é tratada
    como aporte/retirada de caixa, para não misturar "ganho de mercado"
    com "dinheiro novo" — mesma lógica do dashboard original.

    Retorna None se não houver ao menos 2 snapshots com Ibovespa registrado.
    """
    com_ibov = [h for h in historico if h.get("ibov")]
    if len(com_ibov) < 2:
        return None

    rent_acumulada = 1.0
    for anterior, atual in zip(com_ibov, com_ibov[1:]):
        if anterior["totalAtual"] > 0:
            fluxo_caixa = atual["totalInvestido"] - anterior["totalInvestido"]
            retorno_subperiodo = (atual["totalAtual"] - anterior["totalAtual"] - fluxo_caixa) / anterior["totalAtual"]
            rent_acumulada *= (1 + retorno_subperiodo)

    rent_carteira = (rent_acumulada - 1) * 100
    primeiro, ultimo = com_ibov[0], com_ibov[-1]
    rent_ibov = ((ultimo["ibov"] - primeiro["ibov"]) / primeiro["ibov"]) * 100

    return {
        "rent_carteira_pct": rent_carteira,
        "rent_ibov_pct": rent_ibov,
        "data_inicio": primeiro["data"],
        "data_fim": ultimo["data"],
    }


# ==========================================================================
# Preço Teto — Fluxo de Caixa Descontado (modelo de 2 estágios)
# ==========================================================================

@dataclass
class ResultadoFCD:
    preco_teto: float
    preco_teto_com_margem: float
    vp_fluxos: float
    vp_terminal: float
    valor_empresa: float
    valor_equity: float
    projecao: list[dict[str, float]]


def calcular_fcd(
    fcf_base: float, g1_pct: float, anos: int, wacc_pct: float,
    g2_pct: float, divida_liquida: float, n_acoes: float, margem_pct: float,
) -> ResultadoFCD:
    """
    Modelo de Fluxo de Caixa Descontado em 2 estágios (mesma fórmula do
    dashboard original): projeta o FCF crescendo a g1 por `anos`, calcula
    um valor terminal (perpetuidade com crescimento g2) e desconta tudo a
    valor presente pela taxa WACC.

    Levanta ValueError se wacc <= g2 (senão o valor terminal diverge).
    """
    g1 = g1_pct / 100
    wacc = wacc_pct / 100
    g2 = g2_pct / 100
    margem = margem_pct / 100

    if wacc <= g2:
        raise ValueError(
            "A taxa de desconto (WACC) precisa ser maior que a taxa de "
            "crescimento na perpetuidade (g2), senão o valor terminal diverge."
        )

    vp_fluxos = 0.0
    fcf_ano = fcf_base
    projecao = []
    for t in range(1, anos + 1):
        fcf_ano = fcf_ano * (1 + g1)
        vp = fcf_ano / ((1 + wacc) ** t)
        vp_fluxos += vp
        projecao.append({"ano": t, "fcf": fcf_ano, "vp": vp})

    valor_terminal = (fcf_ano * (1 + g2)) / (wacc - g2)
    vp_terminal = valor_terminal / ((1 + wacc) ** anos)
    valor_empresa = vp_fluxos + vp_terminal
    valor_equity = valor_empresa - divida_liquida
    preco_teto = (valor_equity / n_acoes) if n_acoes > 0 else 0.0
    preco_teto_com_margem = preco_teto * (1 - margem)

    return ResultadoFCD(
        preco_teto=preco_teto, preco_teto_com_margem=preco_teto_com_margem,
        vp_fluxos=vp_fluxos, vp_terminal=vp_terminal,
        valor_empresa=valor_empresa, valor_equity=valor_equity, projecao=projecao,
    )


# ==========================================================================
# Totais gerais da carteira (usados nos cards de resumo)
# ==========================================================================

def totais_carteira(posicoes_completas: list[dict[str, Any]]) -> dict[str, float]:
    """Soma total investido/atual/lucro/rentabilidade a partir das posições completas."""
    total_investido = sum(p["valor_total_investido"] for p in posicoes_completas)
    total_atual = sum(p["atual"] for p in posicoes_completas)
    lucro = total_atual - total_investido
    rentabilidade = (lucro / total_investido * 100) if total_investido > 0 else 0.0
    variacao_dia_reais = sum(p["variacao_dia_reais"] or 0 for p in posicoes_completas)
    return {
        "total_investido": total_investido,
        "total_atual": total_atual,
        "lucro": lucro,
        "rentabilidade_pct": rentabilidade,
        "variacao_dia_reais": variacao_dia_reais,
    }
