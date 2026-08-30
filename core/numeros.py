"""
Utilitário pequeno e compartilhado: converter qualquer coisa que devesse
ser um número (vinda do Yahoo Finance, de um JSON antigo etc.) para um
`float` confiável, ou `None` se não for possível.

Extraído para um módulo próprio porque tanto `core/market_data.py`
(preços) quanto `core/fundamentals.py` (indicadores fundamentalistas)
precisam exatamente da mesma proteção — sem ela, um valor "NaN" ou
"infinito" vindo da API consegue atravessar o app inteiro e travar a tela
na hora de formatar (foi exatamente isso que aconteceu com o preço de
alguns ativos antes dessa correção).
"""

from __future__ import annotations

import math
from typing import Any


def numero_valido(valor: Any) -> float | None:
    """Converte para float; descarta None, texto não numérico, NaN e infinito."""
    if valor is None:
        return None
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return None
    return valor if math.isfinite(valor) else None
