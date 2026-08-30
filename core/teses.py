"""
Diário de tese de investimento: por que você comprou (ou está de olho em)
cada ativo, o que espera dele, e o que reavaliar se a tese mudar — pedido
explícito da auditoria ("Diário de tese de investimento por ativo").

Cada ativo tem uma LISTA de entradas (nunca sobrescreve a anterior) — a
ideia é reler mais tarde e comparar o que você escreveu com o que realmente
aconteceu, não manter só a versão mais recente.

Módulo puro (sem Streamlit, sem Firebase) — usado tanto pela aba do PC
(ui/tese_investimento.py) quanto pelo relay que aplica pedidos do celular
(core/pendencias_celular.py) e pelo retrato enviado à nuvem
(core/mobile_snapshot.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core import data_store

LIMITE_CARACTERES_TEXTO = 4000


def adicionar_entrada(dados: dict[str, Any], ticker: str, texto: str) -> dict[str, Any]:
    """
    Acrescenta uma nova entrada na tese de `ticker` (não mexe nas
    anteriores) e devolve a entrada criada ({id, data, texto}).　Levanta
    ValueError se o texto vier vazio ou passar do limite de caracteres —
    quem chama (a tela do PC ou o validador do relay do celular) decide
    como mostrar esse erro.
    """
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("O texto da tese não pode ficar vazio.")
    if len(texto) > LIMITE_CARACTERES_TEXTO:
        raise ValueError(f"O texto da tese não pode passar de {LIMITE_CARACTERES_TEXTO} caracteres.")

    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Informe um ticker.")

    entradas = dados.setdefault("teses", {}).setdefault(ticker, [])
    entrada = {"id": data_store.novo_id(), "data": datetime.now().isoformat(), "texto": texto}
    entradas.append(entrada)
    return entrada


def listar_entradas(dados: dict[str, Any], ticker: str) -> list[dict[str, Any]]:
    """Entradas de um ativo, mais recente primeiro. Lista vazia se nunca escreveu nada para esse ticker."""
    entradas = dados.get("teses", {}).get(ticker.strip().upper(), [])
    return sorted(entradas, key=lambda e: e["data"], reverse=True)


def remover_entrada(dados: dict[str, Any], ticker: str, entrada_id: str) -> bool:
    """Remove uma entrada específica pelo id. Devolve True se removeu algo, False se o id não existia."""
    ticker = ticker.strip().upper()
    entradas = dados.get("teses", {}).get(ticker, [])
    entradas_restantes = [e for e in entradas if e["id"] != entrada_id]
    removeu = len(entradas_restantes) < len(entradas)
    if ticker in dados.get("teses", {}):
        dados["teses"][ticker] = entradas_restantes
    return removeu


def tickers_com_tese(dados: dict[str, Any]) -> list[str]:
    """Tickers que já têm ao menos uma entrada escrita, em ordem alfabética."""
    return sorted(t for t, entradas in dados.get("teses", {}).items() if entradas)
