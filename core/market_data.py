"""
Busca de cotações na B3 via Yahoo Finance, usando a biblioteca `yfinance`.

Por que yfinance? Ele não exige cadastro nem chave de API (token) — só
busca os dados públicos que o próprio site do Yahoo Finance expõe — e é a
forma mais simples de automatizar isso rodando localmente no seu
computador (diferente do dashboard em HTML, que tinha que contornar
bloqueios de CORS do navegador com um proxy).

As funções usam o cache do Streamlit (`st.cache_data`) para não buscar a
mesma cotação repetidamente a cada clique na tela — os dados só ficam
"velhos" por no máximo CACHE_TTL_COTACAO_SEGUNDOS. O botão "🔄 Atualizar
Dados" da barra lateral chama `limpar_cache_cotacoes()` antes de buscar de
novo, então ele sempre força uma consulta nova ao Yahoo Finance.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import streamlit as st
import yfinance as yf

from core.config import (
    CACHE_TTL_COTACAO_SEGUNDOS,
    CACHE_TTL_NOME_EMPRESA_SEGUNDOS,
    SUFIXO_B3,
    TICKER_IBOVESPA,
)
from core.numeros import numero_valido

# Yahoo Finance ocasionalmente responde devagar ou recusa uma requisição
# (timeout / limite de taxa) quando várias consultas seguidas são feitas em
# rajada — o que tende a atingir mais os ÚLTIMOS tickers de uma atualização
# (normalmente as empresas-alvo, buscadas depois das posições da carteira).
# Uma segunda tentativa, com uma pequena pausa, resolve a esmagadora maioria
# desses casos sem deixar o botão perceptivelmente mais lento.
_TENTATIVAS_POR_TICKER = 2
_PAUSA_ENTRE_TENTATIVAS_SEGUNDOS = 0.8
_PAUSA_ENTRE_TICKERS_SEGUNDOS = 0.25


def _valor_fast_info(fast_info: Any, *nomes: str) -> float | None:
    """
    `fast_info` do yfinance às vezes usa nomes em camelCase ("lastPrice") e
    às vezes em snake_case ("last_price"), dependendo da versão instalada —
    tentamos os dois formatos, por atributo e por chave, e ignoramos
    qualquer erro (é normal faltar algum campo para certos ativos).
    """
    for nome in nomes:
        valor = None
        try:
            valor = fast_info[nome]
        except Exception:
            valor = getattr(fast_info, nome, None)
        numero = numero_valido(valor)
        if numero is not None:
            return numero
    return None


def _tentar_buscar_preco_yahoo(symbolo_yahoo: str) -> dict[str, float] | None:
    """Uma única tentativa de busca — ver _buscar_preco_yahoo() para o retry."""
    try:
        ticker_yf = yf.Ticker(symbolo_yahoo)

        preco_atual = None
        preco_anterior = None
        try:
            fast = ticker_yf.fast_info
            preco_atual = _valor_fast_info(fast, "lastPrice", "last_price")
            preco_anterior = _valor_fast_info(fast, "previousClose", "previous_close")
        except Exception:
            pass

        if preco_atual is None or preco_anterior is None:
            historico = ticker_yf.history(period="5d", interval="1d")
            fechamentos = [
                v for v in (numero_valido(x) for x in historico["Close"].tolist())
                if v is not None
            ] if not historico.empty else []
            if preco_atual is None and fechamentos:
                preco_atual = fechamentos[-1]
            if preco_anterior is None and len(fechamentos) >= 2:
                preco_anterior = fechamentos[-2]

        if preco_atual is None:
            return None
        return {"preco": preco_atual, "previousClose": preco_anterior}
    except Exception:
        return None


@st.cache_data(ttl=CACHE_TTL_COTACAO_SEGUNDOS, show_spinner=False)
def _buscar_preco_yahoo(symbolo_yahoo: str) -> dict[str, float] | None:
    """
    Busca preço atual e fechamento anterior para um símbolo do Yahoo
    Finance (ex: "PETR4.SA" ou "^BVSP"). Retorna None se não encontrar um
    preço atual válido depois de todas as tentativas.

    Tenta primeiro `fast_info` (mais perto de tempo real). Quando falta
    algum valor ali — ou quando o pregão do dia ainda está em andamento e
    o Yahoo retorna um fechamento "NaN" para hoje — completa com o
    histórico diário, sempre ignorando entradas sem número válido.

    Repete a busca algumas vezes (_TENTATIVAS_POR_TICKER) antes de desistir:
    o Yahoo Finance ocasionalmente recusa ou atrasa uma resposta no meio de
    uma rajada de consultas — como o resultado desta função fica em cache,
    uma falha transitória sem retry ficaria "presa" como erro até o cache
    expirar, mesmo que uma nova tentativa, segundos depois, funcionasse.
    """
    for tentativa in range(1, _TENTATIVAS_POR_TICKER + 1):
        resultado = _tentar_buscar_preco_yahoo(symbolo_yahoo)
        if resultado is not None:
            return resultado
        if tentativa < _TENTATIVAS_POR_TICKER:
            time.sleep(_PAUSA_ENTRE_TENTATIVAS_SEGUNDOS)
    return None


@st.cache_data(ttl=CACHE_TTL_NOME_EMPRESA_SEGUNDOS, show_spinner=False)
def _buscar_nome_empresa(symbolo_yahoo: str) -> str | None:
    """
    Busca o nome da empresa (cacheado por bem mais tempo, pois não muda).
    Separado da busca de preço porque `.info` é uma chamada mais pesada ao
    Yahoo Finance — não vale a pena repeti-la a cada atualização de preço.

    É justamente por ser uma chamada pesada (e só acontecer, de fato, na
    PRIMEIRA vez que um ticker novo é buscado — os demais dias usam o cache
    de 24h) que ela tende a ser a mais sensível a uma rejeição temporária do
    Yahoo; daí o mesmo retry usado na busca de preço.
    """
    for tentativa in range(1, _TENTATIVAS_POR_TICKER + 1):
        try:
            info = yf.Ticker(symbolo_yahoo).info
            nome = info.get("longName") or info.get("shortName")
            if nome:
                return nome
        except Exception:
            pass
        if tentativa < _TENTATIVAS_POR_TICKER:
            time.sleep(_PAUSA_ENTRE_TENTATIVAS_SEGUNDOS)
    return None


def buscar_cotacao_ativo(ticker: str) -> dict[str, Any] | None:
    """
    Busca a cotação de um ativo da B3 pelo ticker (ex: "PETR4", sem sufixo).
    Retorna um dicionário no mesmo formato salvo em dados["cotacoes"][ticker],
    ou None se a busca falhar.
    """
    symbolo = f"{ticker}{SUFIXO_B3}"
    preco_info = _buscar_preco_yahoo(symbolo)
    if preco_info is None:
        return None
    nome = _buscar_nome_empresa(symbolo) or ticker
    return {
        "preco": preco_info["preco"],
        "previousClose": preco_info["previousClose"],
        "nome": nome,
        "fonte": "Yahoo Finance (yfinance)",
        "atualizadoEm": datetime.now().isoformat(),
    }


def buscar_cotacao_ibovespa() -> float | None:
    """Busca o valor atual do Ibovespa (usado no comparativo da aba Evolução)."""
    info = _buscar_preco_yahoo(TICKER_IBOVESPA)
    return info["preco"] if info else None


def atualizar_cotacoes(tickers: list[str], cotacoes_atuais: dict[str, dict]) -> tuple[dict[str, dict], list[str]]:
    """
    Busca a cotação de cada ticker da lista e devolve um novo dicionário de
    cotações (mesclado com o que já existia) e a lista de tickers que
    falharam. Não modifica `cotacoes_atuais` — quem chama decide se salva
    o resultado.

    Uma pequena pausa entre um ticker e outro evita disparar várias
    requisições em rajada contra o Yahoo Finance — o cenário mais propenso
    a gerar falhas, e que tende a prejudicar justamente os ÚLTIMOS tickers
    da lista (normalmente as empresas-alvo, buscadas depois das posições).
    """
    novas_cotacoes = dict(cotacoes_atuais)
    falhas = []
    for indice, ticker in enumerate(tickers):
        if indice > 0:
            time.sleep(_PAUSA_ENTRE_TICKERS_SEGUNDOS)
        resultado = buscar_cotacao_ativo(ticker)
        if resultado is None:
            falhas.append(ticker)
        else:
            novas_cotacoes[ticker] = resultado
    return novas_cotacoes, falhas


def limpar_cache_cotacoes() -> None:
    """Força a próxima busca a ignorar o cache — usado pelo botão 'Atualizar Dados'."""
    _buscar_preco_yahoo.clear()
    _buscar_nome_empresa.clear()
