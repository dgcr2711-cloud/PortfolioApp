"""
Testes automatizados de core/fundamentals.py: a busca compartilhada de
demonstrações anuais (_buscar_demonstracoes_anuais — usada tanto pelo
Piotroski quanto pelo Altman, ver a docstring da função) e a lógica de
busca em paralelo por vários tickers (atualizar_fundamentos,
buscar_analise_avancada_varios) — mesclagem de resultados, isolamento de
falha por ticker, e o compartilhamento do cache entre Piotroski e Altman.

A extração dos indicadores em si (buscar_fundamentos, buscar_dados_piotroski,
buscar_dados_altman — que depende do FORMATO real que o yfinance devolve
para as demonstrações financeiras) ainda depende do yfinance de verdade
rodando no PC do Diego para ser confirmada por completo (mesma ressalva já
documentada nas próprias funções, ver docstrings). Aqui testamos a parte
que é lógica pura nossa.

Este módulo importa `streamlit` e `yfinance` no TOPO do arquivo, pelo
mesmo motivo (e com o mesmo padrão) de tests/test_market_data.py — leia a
docstring de lá se for mexer aqui. Os arquivos de teste rodam em ordem
alfabética (ver /tmp/rodar_testes_sandbox.py) e "test_fundamentals.py"
vem ANTES de "test_market_data.py", então é este arquivo que registra os
módulos falsos primeiro — o `sys.modules.setdefault(...)` de lá vira
no-op, e ambos os arquivos acabam usando os mesmos módulos falsos daqui
(inofensivo: nenhum dos dois testa `yf.Ticker`/`st.cache_data` de verdade,
sempre trocam a função de mais alto nível por uma versão falsa).

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import sys


class _FalsoDecoradorCacheData:
    """Substitui @st.cache_data(...) por um decorador que não faz cache
    nenhum (só chama a função direto) e expõe um `.clear()` de mentira,
    para `limpar_cache_*()` não quebrarem."""

    def __call__(self, *args, **kwargs):
        def decorador(func):
            def wrapper(*a, **kw):
                return func(*a, **kw)
            wrapper.clear = lambda: None
            return wrapper
        return decorador


class _FalsoModuloStreamlit:
    cache_data = _FalsoDecoradorCacheData()


class _FalsoModuloYfinance:
    """`Ticker` fica None por padrão — os testes deste arquivo que
    precisam de um Ticker de verdade trocam `fundamentals.yf.Ticker`
    diretamente antes de chamar a função (mesmo padrão de `requests.get`
    em tests/test_b3_publico.py), então nunca dependem do valor default
    aqui."""
    Ticker = None


sys.modules.setdefault("streamlit", _FalsoModuloStreamlit())
sys.modules.setdefault("yfinance", _FalsoModuloYfinance())

from core import fundamentals  # noqa: E402  (import depois de injetar os módulos falsos, de propósito)


class _TickerFalso:
    """
    Dublê de yfinance.Ticker: cada atributo (info/financials/balance_sheet
    /cashflow) devolve um valor fixo, ou lança uma exceção quando o valor
    passado for o marcador "__lanca__" — simula aquele campo específico
    falhando na busca, para testar que _buscar_demonstracoes_anuais isola
    a falha de um campo sem derrubar os outros.
    """

    def __init__(self, info=None, financials=None, balance_sheet=None, cashflow=None):
        self._valores = {
            "info": info, "financials": financials,
            "balance_sheet": balance_sheet, "cashflow": cashflow,
        }

    def _obter(self, nome):
        valor = self._valores[nome]
        if valor == "__lanca__":
            raise RuntimeError(f"falha simulada em {nome}")
        return valor

    @property
    def info(self):
        return self._obter("info")

    @property
    def financials(self):
        return self._obter("financials")

    @property
    def balance_sheet(self):
        return self._obter("balance_sheet")

    @property
    def cashflow(self):
        return self._obter("cashflow")


# ==========================================================================
# _buscar_demonstracoes_anuais
# ==========================================================================

def test_buscar_demonstracoes_anuais_junta_os_4_campos():
    original = fundamentals.yf.Ticker
    fundamentals.yf.Ticker = lambda symbolo: _TickerFalso(
        info={"marketCap": 100}, financials="fin", balance_sheet="bal", cashflow="cf",
    )
    try:
        resultado = fundamentals._buscar_demonstracoes_anuais("PETR4.SA")
        assert resultado == {
            "info": {"marketCap": 100}, "financials": "fin",
            "balance_sheet": "bal", "cashflow": "cf",
        }
    finally:
        fundamentals.yf.Ticker = original


def test_buscar_demonstracoes_anuais_isola_falha_de_um_campo():
    original = fundamentals.yf.Ticker
    fundamentals.yf.Ticker = lambda symbolo: _TickerFalso(
        info={"marketCap": 100}, financials="fin", balance_sheet="__lanca__", cashflow="cf",
    )
    try:
        resultado = fundamentals._buscar_demonstracoes_anuais("PETR4.SA")
        assert resultado["info"] == {"marketCap": 100}
        assert resultado["financials"] == "fin"
        assert resultado["balance_sheet"] is None  # falhou, mas não derrubou os outros 3
        assert resultado["cashflow"] == "cf"
    finally:
        fundamentals.yf.Ticker = original


def test_buscar_demonstracoes_anuais_ticker_falha_ao_construir():
    original = fundamentals.yf.Ticker

    def _lanca(symbolo):
        raise RuntimeError("símbolo inválido")

    fundamentals.yf.Ticker = _lanca
    try:
        resultado = fundamentals._buscar_demonstracoes_anuais("XXXX.SA")
        assert resultado == {"info": None, "financials": None, "balance_sheet": None, "cashflow": None}
    finally:
        fundamentals.yf.Ticker = original


# ==========================================================================
# atualizar_fundamentos — busca em paralelo
# ==========================================================================

def test_atualizar_fundamentos_mescla_e_lista_falhas():
    original = fundamentals.buscar_fundamentos
    dados_novos = {"PETR4": {"pl": 5.0}, "ITUB4": {"pl": 8.0}}
    fundamentals.buscar_fundamentos = lambda ticker: dados_novos.get(ticker)
    try:
        existentes = {"VALE3": {"pl": 4.0}}  # ticker que não está sendo atualizado agora
        novos, falhas = fundamentals.atualizar_fundamentos(["PETR4", "ITUB4", "CMIG4"], existentes)
        assert novos["PETR4"] == {"pl": 5.0}
        assert novos["ITUB4"] == {"pl": 8.0}
        assert novos["VALE3"] == {"pl": 4.0}  # preservado
        assert falhas == ["CMIG4"]  # não veio em dados_novos -> buscar_fundamentos devolveu None
        assert existentes == {"VALE3": {"pl": 4.0}}  # dict original não foi modificado
    finally:
        fundamentals.buscar_fundamentos = original


def test_atualizar_fundamentos_lista_vazia():
    novos, falhas = fundamentals.atualizar_fundamentos([], {"PETR4": {"pl": 5.0}})
    assert novos == {"PETR4": {"pl": 5.0}}
    assert falhas == []


# ==========================================================================
# buscar_analise_avancada_varios — busca em paralelo (Piotroski + Altman)
# ==========================================================================

def test_buscar_analise_avancada_varios_junta_piotroski_e_altman_por_ticker():
    original_piotroski = fundamentals.buscar_dados_piotroski
    original_altman = fundamentals.buscar_dados_altman
    piotroski_por_ticker = {"PETR4": {"pontos": 7}}  # ITUB4 sem Piotroski (ex: só 1 ano de balanço)
    altman_por_ticker = {"PETR4": {"zScore": 3.0}, "ITUB4": {"zScore": 1.5}}
    fundamentals.buscar_dados_piotroski = lambda ticker: piotroski_por_ticker.get(ticker)
    fundamentals.buscar_dados_altman = lambda ticker: altman_por_ticker.get(ticker)
    try:
        piotroski_resultado, altman_resultado = fundamentals.buscar_analise_avancada_varios(["PETR4", "ITUB4"])
        assert piotroski_resultado == {"PETR4": {"pontos": 7}}
        assert altman_resultado == {"PETR4": {"zScore": 3.0}, "ITUB4": {"zScore": 1.5}}
    finally:
        fundamentals.buscar_dados_piotroski = original_piotroski
        fundamentals.buscar_dados_altman = original_altman


def test_buscar_analise_avancada_varios_ticker_com_excecao_nao_derruba_os_outros():
    original_piotroski = fundamentals.buscar_dados_piotroski
    original_altman = fundamentals.buscar_dados_altman

    def _piotroski(ticker):
        if ticker == "VALE3":
            raise RuntimeError("falha simulada")
        return {"pontos": 5}

    fundamentals.buscar_dados_piotroski = _piotroski
    fundamentals.buscar_dados_altman = lambda ticker: {"zScore": 2.0}
    try:
        piotroski_resultado, altman_resultado = fundamentals.buscar_analise_avancada_varios(["PETR4", "VALE3"])
        assert piotroski_resultado == {"PETR4": {"pontos": 5}}  # VALE3 ficou de fora (só ele que falhou)
        assert altman_resultado == {"PETR4": {"zScore": 2.0}, "VALE3": {"zScore": 2.0}}  # Altman não foi afetado
    finally:
        fundamentals.buscar_dados_piotroski = original_piotroski
        fundamentals.buscar_dados_altman = original_altman


def test_buscar_analise_avancada_varios_lista_vazia():
    piotroski_resultado, altman_resultado = fundamentals.buscar_analise_avancada_varios([])
    assert piotroski_resultado == {}
    assert altman_resultado == {}
