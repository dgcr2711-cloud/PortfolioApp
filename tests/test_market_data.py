"""
Testes automatizados de core/market_data.py — só a parte de "Próximo
Dividendo previsto" (normalização de datas do yfinance, extração dos
campos do calendar/info, e a filtragem/ordenação da lista de próximos
dividendos) é testada aqui: o resto do módulo (busca de preço/cotação)
depende inteiramente da rede/Yahoo Finance de verdade e não tem lógica
pura própria para testar isoladamente.

Este módulo importa `streamlit` e `yfinance` no TOPO do arquivo (para usar
o cache do Streamlit e a biblioteca do Yahoo Finance) — nenhum dos dois
está instalado neste sandbox (sem acesso à internet para instalar
pacotes), então o simples `import core.market_data` quebra com
ModuleNotFoundError se não houver módulos falsos em sys.modules ANTES do
import. Por isso, diferente do padrão usado em
tests/test_notificacoes_whatsapp.py (que só importa streamlit dentro de
uma função, podendo trocar o falso por teste), aqui os módulos falsos são
injetados uma única vez, no topo deste arquivo, antes do `from core import
market_data` — e ficam em sys.modules pelo resto da execução dos testes
(inofensivo: nenhum outro teste espera "yfinance" ausente, e os testes de
notificações que mexem em "streamlit" sempre salvam/restauram o que
encontraram, então continuam funcionando normalmente).

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import sys
from datetime import date, datetime


class _FalsoDecoradorCacheData:
    """Substitui @st.cache_data(...) por um decorador que não faz cache
    nenhum (só chama a função direto) e expõe um `.clear()` de mentira,
    para `limpar_cache_dividendos()`/`limpar_cache_cotacoes()` não quebrarem."""

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
    """`Ticker` fica None por padrão — os testes deste arquivo não chamam
    `yf.Ticker(...)` diretamente (testam as funções internas com um
    dublê de ticker próprio, ou trocam `market_data.buscar_proximo_dividendo`
    inteiro), então nunca precisam de um `Ticker` de verdade."""
    Ticker = None


sys.modules.setdefault("streamlit", _FalsoModuloStreamlit())
sys.modules.setdefault("yfinance", _FalsoModuloYfinance())

from core import market_data  # noqa: E402  (import depois de injetar os módulos falsos, de propósito)


# ==========================================================================
# _normalizar_data_yahoo
# ==========================================================================

def test_normalizar_data_yahoo_aceita_objeto_date():
    assert market_data._normalizar_data_yahoo(date(2026, 9, 15)) == date(2026, 9, 15)


def test_normalizar_data_yahoo_aceita_datetime():
    assert market_data._normalizar_data_yahoo(datetime(2026, 9, 15, 10, 30)) == date(2026, 9, 15)


def test_normalizar_data_yahoo_aceita_timestamp_unix():
    timestamp = datetime(2026, 9, 15, 12, 0).timestamp()
    assert market_data._normalizar_data_yahoo(timestamp) == date(2026, 9, 15)


def test_normalizar_data_yahoo_none_para_valor_invalido():
    assert market_data._normalizar_data_yahoo(None) is None
    assert market_data._normalizar_data_yahoo("não é uma data") is None
    assert market_data._normalizar_data_yahoo([1, 2, 3]) is None


# ==========================================================================
# _extrair_data_do_calendar / _extrair_data_do_info
# ==========================================================================

class _TickerFalso:
    """Dublê de yf.Ticker(...) — só implementa `.calendar` e `.info` como
    propriedades (que podem lançar exceção, simulando o Yahoo Finance
    fora do ar ou o ativo sem esse dado)."""

    def __init__(self, calendar=None, info=None, calendar_lanca=False, info_lanca=False):
        self._calendar = calendar
        self._info = info
        self._calendar_lanca = calendar_lanca
        self._info_lanca = info_lanca

    @property
    def calendar(self):
        if self._calendar_lanca:
            raise RuntimeError("Yahoo Finance fora do ar (simulado)")
        return self._calendar

    @property
    def info(self):
        if self._info_lanca:
            raise RuntimeError("Yahoo Finance fora do ar (simulado)")
        return self._info


def test_extrair_data_do_calendar_usa_dividend_date():
    ticker = _TickerFalso(calendar={"Dividend Date": date(2026, 9, 15)})
    assert market_data._extrair_data_do_calendar(ticker) == date(2026, 9, 15)


def test_extrair_data_do_calendar_usa_ex_dividend_date_como_fallback():
    ticker = _TickerFalso(calendar={"Ex-Dividend Date": date(2026, 9, 10)})
    assert market_data._extrair_data_do_calendar(ticker) == date(2026, 9, 10)


def test_extrair_data_do_calendar_none_quando_calendar_nao_e_dict():
    assert market_data._extrair_data_do_calendar(_TickerFalso(calendar=None)) is None
    assert market_data._extrair_data_do_calendar(_TickerFalso(calendar=[])) is None


def test_extrair_data_do_calendar_none_quando_lanca_excecao():
    assert market_data._extrair_data_do_calendar(_TickerFalso(calendar_lanca=True)) is None


def test_extrair_data_do_info_usa_ex_dividend_date():
    timestamp = datetime(2026, 10, 1, 9, 0).timestamp()
    ticker = _TickerFalso(info={"exDividendDate": timestamp})
    assert market_data._extrair_data_do_info(ticker) == date(2026, 10, 1)


def test_extrair_data_do_info_none_quando_lanca_excecao():
    assert market_data._extrair_data_do_info(_TickerFalso(info_lanca=True)) is None


def test_extrair_data_do_info_none_quando_info_nao_e_dict():
    assert market_data._extrair_data_do_info(_TickerFalso(info=None)) is None


# ==========================================================================
# buscar_proximos_dividendos — filtragem e ordenação
# ==========================================================================

def test_buscar_proximos_dividendos_so_inclui_tickers_com_data_encontrada():
    original = market_data.buscar_proximo_dividendo
    datas = {"PETR4": date(2026, 9, 20), "VALE3": None, "ITUB4": date(2026, 9, 5)}
    market_data.buscar_proximo_dividendo = lambda ticker: datas[ticker]
    try:
        resultado = market_data.buscar_proximos_dividendos(["PETR4", "VALE3", "ITUB4"])
        assert [r["ticker"] for r in resultado] == ["ITUB4", "PETR4"]  # VALE3 ficou de fora (sem data)
    finally:
        market_data.buscar_proximo_dividendo = original


def test_buscar_proximos_dividendos_ordena_pela_data_mais_proxima():
    original = market_data.buscar_proximo_dividendo
    datas = {"AAAA3": date(2026, 12, 1), "BBBB3": date(2026, 9, 1), "CCCC3": date(2026, 10, 15)}
    market_data.buscar_proximo_dividendo = lambda ticker: datas[ticker]
    try:
        resultado = market_data.buscar_proximos_dividendos(list(datas.keys()))
        assert [r["ticker"] for r in resultado] == ["BBBB3", "CCCC3", "AAAA3"]
    finally:
        market_data.buscar_proximo_dividendo = original


def test_buscar_proximos_dividendos_lista_vazia_sem_tickers():
    assert market_data.buscar_proximos_dividendos([]) == []
