"""
Métricas de carteira em nível agregado — o tipo de leitura que vem depois
de olhar ativo por ativo: "essa carteira, como um todo, está bem
construída?" Concentração, diversificação setorial, indicadores
fundamentalistas ponderados pelo peso de cada posição, crescimento anual
aproximado (CAGR) e a maior perda já registrada (drawdown simplificado).

Assim como core/calculations.py, este módulo é puro: só recebe listas e
dicionários e devolve números — sem depender do Streamlit nem da internet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from core.config import LIMITE_CONCENTRACAO_ALERTA_PCT


# ==========================================================================
# Concentração e diversificação
# ==========================================================================

def concentracao_por_ativo(posicoes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """% do patrimônio atual em cada ativo, do maior para o menor peso."""
    total = sum(p["atual"] for p in posicoes)
    if total <= 0:
        return []
    linhas = [{"ticker": p["ticker"], "valor": p["atual"], "peso_pct": p["atual"] / total * 100} for p in posicoes]
    return sorted(linhas, key=lambda l: l["peso_pct"], reverse=True)


@dataclass
class DiagnosticoConcentracao:
    maior_ticker: str | None
    maior_peso_pct: float
    indice_hhi: float          # Índice Herfindahl-Hirschman (0 a 1) — quanto maior, mais concentrada
    classificacao_hhi: str     # "baixa" | "moderada" | "alta"
    alerta_concentracao: bool  # True se o maior ativo sozinho passa do limite configurado


def diagnostico_concentracao(
    lista_concentracao: list[dict[str, Any]], limite_alerta_pct: float = LIMITE_CONCENTRACAO_ALERTA_PCT
) -> DiagnosticoConcentracao:
    """
    Índice Herfindahl-Hirschman (HHI): soma dos quadrados dos pesos (em
    fração, não em %). É a mesma métrica usada por reguladores para medir
    concentração de mercado — aqui aplicada aos pesos da própria carteira.
    Referência usual: HHI < 0.15 é diversificação baixa (boa), 0.15–0.25
    moderada, acima de 0.25 é alta concentração.
    """
    if not lista_concentracao:
        return DiagnosticoConcentracao(None, 0.0, 0.0, "baixa", False)

    hhi = sum((c["peso_pct"] / 100) ** 2 for c in lista_concentracao)
    if hhi < 0.15:
        classificacao = "baixa"
    elif hhi < 0.25:
        classificacao = "moderada"
    else:
        classificacao = "alta"

    maior = lista_concentracao[0]
    return DiagnosticoConcentracao(
        maior_ticker=maior["ticker"],
        maior_peso_pct=maior["peso_pct"],
        indice_hhi=hhi,
        classificacao_hhi=classificacao,
        alerta_concentracao=maior["peso_pct"] > limite_alerta_pct,
    )


def diversificacao_setorial(posicoes: list[dict[str, Any]], setores: dict[str, str]) -> list[dict[str, Any]]:
    """% do patrimônio atual por setor, do maior para o menor."""
    total = sum(p["atual"] for p in posicoes)
    if total <= 0:
        return []
    por_setor: dict[str, float] = {}
    for p in posicoes:
        setor = setores.get(p["ticker"]) or "Sem setor definido"
        por_setor[setor] = por_setor.get(setor, 0.0) + p["atual"]
    linhas = [{"setor": s, "valor": v, "peso_pct": v / total * 100} for s, v in por_setor.items()]
    return sorted(linhas, key=lambda l: l["peso_pct"], reverse=True)


# ==========================================================================
# Desempenho ao longo do tempo: CAGR aproximado e maior perda registrada
# ==========================================================================

def cagr_aproximado(historico: list[dict[str, Any]]) -> float | None:
    """
    Taxa de crescimento anualizada aproximada. Usa o mesmo raciocínio do
    comparativo com o Ibovespa (TWR): a variação do total investido entre
    snapshots é tratada como aporte/retirada, não como ganho de mercado.
    O resultado acumulado é depois anualizado pelo número de dias entre o
    primeiro e o último snapshot.

    Retorna None com menos de 2 snapshots ou menos de ~1 mês de histórico
    (anualizar um período muito curto produz um número exagerado e
    enganoso — melhor não mostrar do que mostrar algo distorcido).
    """
    if len(historico) < 2:
        return None

    rent_acumulada = 1.0
    for anterior, atual in zip(historico, historico[1:]):
        if anterior["totalAtual"] > 0:
            fluxo_caixa = atual["totalInvestido"] - anterior["totalInvestido"]
            retorno_subperiodo = (atual["totalAtual"] - anterior["totalAtual"] - fluxo_caixa) / anterior["totalAtual"]
            rent_acumulada *= (1 + retorno_subperiodo)

    dias = (date.fromisoformat(historico[-1]["data"][:10]) - date.fromisoformat(historico[0]["data"][:10])).days
    if dias < 30:
        return None
    anos = dias / 365.25
    return ((rent_acumulada ** (1 / anos)) - 1) * 100


def maior_perda_registrada(historico: list[dict[str, Any]]) -> float | None:
    """
    Maior queda (%) do patrimônio atual em relação ao pico anterior, entre
    os snapshots disponíveis — um drawdown simplificado (só olha os pontos
    salvos, não o intradia). Serve como lembrete de que toda carteira tem
    períodos de queda, mesmo as bem escolhidas.
    """
    if len(historico) < 2:
        return None
    pior_queda = 0.0
    pico = historico[0]["totalAtual"]
    for h in historico[1:]:
        pico = max(pico, h["totalAtual"])
        if pico > 0:
            queda = (h["totalAtual"] - pico) / pico * 100
            pior_queda = min(pior_queda, queda)
    return pior_queda


# ==========================================================================
# Fundamentos ponderados pela carteira
# ==========================================================================

def fundamentos_ponderados(posicoes: list[dict[str, Any]], fundamentos: dict[str, dict]) -> dict[str, float | None]:
    """
    Média dos principais indicadores fundamentalistas, ponderada pelo peso
    de cada ativo no patrimônio atual — uma leitura de "o fundamento médio"
    da carteira como um todo. Ativos sem fundamento buscado ainda são
    simplesmente ignorados na média (não entram como zero).
    """
    total = sum(p["atual"] for p in posicoes)
    if total <= 0:
        return {"pl": None, "pvp": None, "dividend_yield": None, "roe": None, "cobertura_pct": 0.0}

    def media_ponderada(campo: str) -> tuple[float | None, float]:
        soma_peso = 0.0
        soma_valor = 0.0
        for p in posicoes:
            f = fundamentos.get(p["ticker"])
            if not f or f.get(campo) is None:
                continue
            peso = p["atual"] / total
            soma_valor += f[campo] * peso
            soma_peso += peso
        media = (soma_valor / soma_peso) if soma_peso > 0 else None
        return media, soma_peso

    pl, peso_pl = media_ponderada("pl")
    pvp, _ = media_ponderada("pvp")
    dy, _ = media_ponderada("dividend_yield")
    roe, _ = media_ponderada("roe")

    # % do patrimônio para o qual já existe fundamento buscado — mostra ao
    # usuário quão completa é a leitura (ex.: "cobre 83% da carteira").
    tickers_com_fundamento = {p["ticker"] for p in posicoes if fundamentos.get(p["ticker"])}
    valor_coberto = sum(p["atual"] for p in posicoes if p["ticker"] in tickers_com_fundamento)
    cobertura_pct = (valor_coberto / total * 100) if total > 0 else 0.0

    return {"pl": pl, "pvp": pvp, "dividend_yield": dy, "roe": roe, "cobertura_pct": cobertura_pct}
