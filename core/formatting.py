"""
Formatação de números no padrão brasileiro (R$ 1.234,56 / 12,34%).

Implementado "na mão" (sem depender do módulo `locale` do Python) porque
`locale` exige que o sistema operacional tenha o locale pt_BR instalado —
o que nem sempre é verdade no Windows. Assim o app funciona igual em
qualquer computador, sem configuração extra.
"""

from __future__ import annotations

import math


def formatar_moeda(valor: float | None) -> str:
    """
    Formata um número como moeda brasileira: 1234.5 -> 'R$ 1.234,50'.

    Trata None, NaN e infinito como "sem valor" em vez de deixar o erro
    estourar na tela — o Yahoo Finance ocasionalmente devolve um preço
    "NaN" (não-número) para o pregão do dia ainda em andamento, e sem essa
    proteção isso travava a tela inteira em vez de só mostrar "—".
    """
    if valor is None or (isinstance(valor, float) and not math.isfinite(valor)):
        return "R$ —"
    negativo = valor < 0
    valor = abs(valor)
    inteiro, decimal = f"{valor:,.2f}".split(".")
    # f"{valor:,.2f}" usa vírgula pra milhar e ponto pra decimal (padrão EUA);
    # trocamos os dois para ficar no padrão brasileiro.
    inteiro_br = inteiro.replace(",", ".")
    texto = f"R$ {inteiro_br},{decimal}"
    return f"-{texto}" if negativo else texto


def formatar_moeda_priv(valor: float | None, ocultar: bool) -> str:
    """Igual a formatar_moeda, mas mascara o valor quando o modo privacidade está ativo."""
    return "R$ ••••••" if ocultar else formatar_moeda(valor)


def formatar_pct(valor: float | None, casas: int = 2) -> str:
    """Formata uma fração/percentual: 12.345 -> '12,35%'. Aceita None/NaN -> '—'."""
    if valor is None or (isinstance(valor, float) and not math.isfinite(valor)):
        return "—"
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto}%"


def formatar_numero(valor: float | None, casas: int = 2) -> str:
    """Formata um número simples no padrão brasileiro (sem símbolo de moeda)."""
    if valor is None or (isinstance(valor, float) and not math.isfinite(valor)):
        return "—"
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def mascarar_qtd(qtd: float | int, ocultar: bool) -> str:
    """Mascara a quantidade de ações quando o modo privacidade está ativo."""
    if ocultar:
        return "•••"
    if float(qtd).is_integer():
        return str(int(qtd))
    return formatar_numero(qtd, 4)


def formatar_data_br(data_iso: str | None) -> str:
    """Converte 'YYYY-MM-DD' para 'DD/MM/AAAA'. Retorna '—' se vazio/inválido."""
    if not data_iso or len(data_iso) < 10:
        return "—"
    ano, mes, dia = data_iso[:10].split("-")
    return f"{dia}/{mes}/{ano}"
