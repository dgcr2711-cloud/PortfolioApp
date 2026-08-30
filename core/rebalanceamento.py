"""
Rebalanceamento — compara o peso ATUAL de cada ativo na carteira com uma
meta de alocação definida por VOCÊ (dados["metasAlocacao"], ticker -> %
alvo do patrimônio) e aponta os desvios acima de um limiar configurável,
junto com uma sugestão de quanto comprar/vender (em R$) para voltar à meta.

Só entram nesta conta os tickers que TÊM uma meta definida explicitamente —
um ativo comprado sem meta ainda não é tratado como "deveria ter 0%", só
como "sem meta configurada" (evita um alerta de venda espúrio assim que
você compra algo novo, antes de decidir o tamanho que ele deve ter na
carteira).

Módulo puro: só recebe posições já calculadas (core.calculations) e o
dicionário de metas — não fala com Yahoo Finance nem Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.portfolio_analytics import concentracao_por_ativo

# Desvio (em pontos percentuais, não em % relativo) acima do qual um ativo
# soa alerta de "precisa rebalancear". Ex: meta 20%, atual 26% -> desvio de
# 6 pontos percentuais -> alerta com o limiar padrão de 5.
LIMIAR_ALERTA_PADRAO_PP = 5.0


@dataclass
class DesvioAlocacao:
    ticker: str
    meta_pct: float
    atual_pct: float
    desvio_pp: float     # atual_pct - meta_pct: positivo = acima da meta (venderia), negativo = abaixo (compraria)
    valor_atual: float
    valor_alvo: float
    valor_ajuste: float  # valor_alvo - valor_atual: positivo = precisa COMPRAR, negativo = precisa VENDER
    alerta: bool


def calcular_desvios(
    posicoes: list[dict[str, Any]],
    metas_pct: dict[str, float],
    limiar_alerta_pp: float = LIMIAR_ALERTA_PADRAO_PP,
) -> list[DesvioAlocacao]:
    """
    Uma linha por ticker COM meta definida, ordenada pelo maior desvio
    absoluto primeiro (o que mais precisa de atenção no topo). Um ticker com
    meta mas sem posição hoje entra com atual_pct=0 (sugestão: comprar até
    chegar na meta). Patrimônio total zero -> lista vazia (nada pra
    rebalancear sem dinheiro investido).
    """
    if not metas_pct:
        return []

    total = sum(p["atual"] for p in posicoes)
    if total <= 0:
        return []

    atuais_por_ticker = {c["ticker"]: c for c in concentracao_por_ativo(posicoes)}

    resultado = []
    for ticker in sorted(metas_pct):
        meta_pct = metas_pct[ticker]
        atual = atuais_por_ticker.get(ticker)
        atual_pct = atual["peso_pct"] if atual else 0.0
        valor_atual = atual["valor"] if atual else 0.0
        valor_alvo = total * (meta_pct / 100)
        desvio_pp = atual_pct - meta_pct
        resultado.append(DesvioAlocacao(
            ticker=ticker,
            meta_pct=meta_pct,
            atual_pct=atual_pct,
            desvio_pp=desvio_pp,
            valor_atual=valor_atual,
            valor_alvo=valor_alvo,
            valor_ajuste=valor_alvo - valor_atual,
            alerta=abs(desvio_pp) > limiar_alerta_pp,
        ))

    return sorted(resultado, key=lambda d: abs(d.desvio_pp), reverse=True)


def soma_metas_pct(metas_pct: dict[str, float]) -> float:
    """Soma simples das metas configuradas — usada só para avisar o usuário
    quando ultrapassa 100% (não é um erro que o app impeça, só um aviso: é
    perfeitamente válido deixar parte da carteira "sem meta")."""
    return sum(metas_pct.values())
