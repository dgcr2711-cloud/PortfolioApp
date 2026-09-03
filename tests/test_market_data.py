"""
Testes automatizados de core/market_data.py: a parte de "Próximo
Dividendo previsto" (normalização de datas do yfinance, extração dos
campos do calendar/info, e a filtragem/ordenação da lista de próximos
dividendos), e a lógica de busca em paralelo por vários tickers
(_buscar_em_paralelo/atualizar_cotacoes — mesclagem de resultados, lista
de falhas, isolamento de exceção por ticker). A busca de UM ticker em si
(_buscar_preco_yahoo, _buscar_nome_empresa etc.) depende inteiramente da
rede/Yahoo Finance de verdade e não tem lógica pura própria para testar
isoladamente — por isso os testes acima sempre trocam a função de busca
de 1 ticker por uma versão falsa antes de chamar a função "várias".

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

import requests


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


# ==========================================================================
# _buscar_em_paralelo / atualizar_cotacoes — 2026-09-03, otimização de
# performance: as buscas por ticker passaram a rodar em paralelo (threads)
# em vez de uma de cada vez com pausa entre elas.
# ==========================================================================

def test_buscar_em_paralelo_junta_so_os_resultados_nao_none():
    def busca(ticker):
        return None if ticker == "VALE3" else f"resultado-{ticker}"

    resultado = market_data._buscar_em_paralelo(["PETR4", "VALE3", "ITUB4"], busca)
    assert resultado == {"PETR4": "resultado-PETR4", "ITUB4": "resultado-ITUB4"}


def test_buscar_em_paralelo_lista_vazia():
    assert market_data._buscar_em_paralelo([], lambda t: t) == {}


def test_buscar_em_paralelo_excecao_isolada_nao_derruba_os_outros():
    def busca(ticker):
        if ticker == "VALE3":
            raise RuntimeError("falha simulada")
        return f"ok-{ticker}"

    resultado = market_data._buscar_em_paralelo(["PETR4", "VALE3", "ITUB4"], busca)
    assert resultado == {"PETR4": "ok-PETR4", "ITUB4": "ok-ITUB4"}


def test_atualizar_cotacoes_mescla_com_as_existentes_e_lista_falhas():
    original = market_data.buscar_cotacao_ativo
    cotacoes_novas = {
        "PETR4": {"preco": 38.5},
        "ITUB4": {"preco": 34.2},
    }
    market_data.buscar_cotacao_ativo = lambda ticker: cotacoes_novas.get(ticker)
    try:
        existentes = {"VALE3": {"preco": 60.0}}  # ticker que não está sendo atualizado agora
        novas, falhas = market_data.atualizar_cotacoes(["PETR4", "ITUB4", "CMIG4"], existentes)
        assert novas["PETR4"] == {"preco": 38.5}
        assert novas["ITUB4"] == {"preco": 34.2}
        assert novas["VALE3"] == {"preco": 60.0}  # preservado, não fazia parte da busca
        assert falhas == ["CMIG4"]  # não veio em cotacoes_novas -> buscar_cotacao_ativo devolveu None
        assert existentes == {"VALE3": {"preco": 60.0}}  # dict original não foi modificado
    finally:
        market_data.buscar_cotacao_ativo = original


def test_atualizar_cotacoes_lista_vazia():
    novas, falhas = market_data.atualizar_cotacoes([], {"PETR4": {"preco": 1.0}})
    assert novas == {"PETR4": {"preco": 1.0}}
    assert falhas == []


# ==========================================================================
# HG Brasil Finance (2026-09-03) — troca requests.get e
# market_data._obter_chave_hgbrasil por dublês, igual ao padrão já usado em
# tests/test_b3_publico.py. Cada teste reseta os caches "simples por
# timestamp" no início, pra um teste nunca depender da ordem de execução.
# ==========================================================================

class _RespostaHgBrasilFalsa:
    def __init__(self, status_code=200, corpo=None):
        self.status_code = status_code
        self._corpo = corpo

    def json(self):
        return self._corpo


def _resetar_caches_hgbrasil():
    market_data._cache_taxas_economicas["valor"] = None
    market_data._cache_taxas_economicas["buscado_em"] = 0.0
    market_data._cache_cotacoes_hgbrasil.clear()


def test_obter_chave_hgbrasil_le_do_arquivo_local(tmp_path=None):
    import json

    original = market_data.CAMINHO_CHAVE_HGBRASIL
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as pasta_tmp:
        caminho = Path(pasta_tmp) / "hgbrasil_api_key.json"
        caminho.write_text(json.dumps({"api_key": "chave-de-teste"}), encoding="utf-8")
        market_data.CAMINHO_CHAVE_HGBRASIL = caminho
        try:
            assert market_data._obter_chave_hgbrasil() == "chave-de-teste"
        finally:
            market_data.CAMINHO_CHAVE_HGBRASIL = original


def test_obter_chave_hgbrasil_none_quando_nao_configurada():
    original = market_data.CAMINHO_CHAVE_HGBRASIL
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as pasta_tmp:
        market_data.CAMINHO_CHAVE_HGBRASIL = Path(pasta_tmp) / "nao-existe.json"
        try:
            assert market_data._obter_chave_hgbrasil() is None
        finally:
            market_data.CAMINHO_CHAVE_HGBRASIL = original


def test_buscar_taxas_economicas_sem_chave_devolve_none():
    _resetar_caches_hgbrasil()
    original = market_data._obter_chave_hgbrasil
    market_data._obter_chave_hgbrasil = lambda: None
    try:
        assert market_data.buscar_taxas_economicas() is None
    finally:
        market_data._obter_chave_hgbrasil = original


def test_buscar_taxas_economicas_caminho_feliz():
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = lambda *a, **kw: _RespostaHgBrasilFalsa(
        200, {"results": {"taxes": [{"date": "2026-09-01", "selic": 14.25, "cdi": 14.15}]}}
    )
    try:
        resultado = market_data.buscar_taxas_economicas()
        assert resultado is not None
        assert resultado["selic"] == 14.25
        assert resultado["cdi"] == 14.15
        assert resultado["data"] == "2026-09-01"
        assert resultado["fonte"] == "HG Brasil Finance"
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_taxas_economicas_usa_cache_na_segunda_chamada():
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    chamadas = {"total": 0}

    def get_fake(*a, **kw):
        chamadas["total"] += 1
        return _RespostaHgBrasilFalsa(200, {"results": {"taxes": [{"date": "2026-09-01", "selic": 14.25, "cdi": 14.15}]}})

    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = get_fake
    try:
        market_data.buscar_taxas_economicas()
        market_data.buscar_taxas_economicas()
        assert chamadas["total"] == 1  # segunda chamada veio do cache, não fez requisição de novo
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_taxas_economicas_erro_de_rede_vira_none():
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"

    def levanta(*a, **kw):
        raise requests.exceptions.ConnectionError("sem internet (simulado)")

    requests.get = levanta
    try:
        assert market_data.buscar_taxas_economicas() is None
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_taxas_economicas_falha_tambem_usa_cache_na_segunda_chamada():
    """
    Regressão real (2026-09-03): a primeira versão só cacheava o CAMINHO
    FELIZ — uma falha repetida (chave com problema, plano insuficiente,
    instabilidade) fazia CADA clique em "🔄 Atualizar Dados" esperar o
    timeout inteiro de novo, deixando o app "quase travando". O cache
    precisa cobrir sucesso E falha (com um prazo mais curto pra falha,
    CACHE_TTL_FALHA_HGBRASIL_SEGUNDOS) — este teste garante que uma
    segunda chamada logo depois de uma falha NÃO dispara outra requisição.
    """
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    chamadas = {"total": 0}

    def get_fake(*a, **kw):
        chamadas["total"] += 1
        return _RespostaHgBrasilFalsa(403, None)  # chave inválida/sem permissão, por exemplo

    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = get_fake
    try:
        assert market_data.buscar_taxas_economicas() is None
        assert market_data.buscar_taxas_economicas() is None
        assert chamadas["total"] == 1  # a segunda chamada veio do cache de falha, não bateu na rede de novo
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_cotacoes_hgbrasil_falha_tambem_usa_cache_na_segunda_chamada():
    """Mesma regressão do teste acima, para o plano B de cotações."""
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    chamadas = {"total": 0}

    def get_fake(*a, **kw):
        chamadas["total"] += 1
        return _RespostaHgBrasilFalsa(402, None)

    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = get_fake
    try:
        assert market_data.buscar_cotacoes_hgbrasil(["PETR4"]) == {}
        assert market_data.buscar_cotacoes_hgbrasil(["PETR4"]) == {}
        assert chamadas["total"] == 1
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_taxas_economicas_status_diferente_de_200_vira_none():
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = lambda *a, **kw: _RespostaHgBrasilFalsa(403, None)
    try:
        assert market_data.buscar_taxas_economicas() is None
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_cotacoes_hgbrasil_lista_vazia_nao_faz_requisicao():
    _resetar_caches_hgbrasil()
    get_original = requests.get
    requests.get = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("não deveria chamar requests.get"))
    try:
        assert market_data.buscar_cotacoes_hgbrasil([]) == {}
    finally:
        requests.get = get_original


def test_buscar_cotacoes_hgbrasil_sem_chave_devolve_vazio():
    _resetar_caches_hgbrasil()
    original = market_data._obter_chave_hgbrasil
    market_data._obter_chave_hgbrasil = lambda: None
    try:
        assert market_data.buscar_cotacoes_hgbrasil(["PETR4"]) == {}
    finally:
        market_data._obter_chave_hgbrasil = original


def test_buscar_cotacoes_hgbrasil_caminho_feliz_varios_tickers():
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = lambda *a, **kw: _RespostaHgBrasilFalsa(200, {"results": [
        {"symbol": "PETR4", "name": "Petrobrás", "price": 29.45, "change_price": 0.50},
        {"symbol": "VALE3", "name": "Vale", "price": 60.10, "change_price": -0.30},
    ]})
    try:
        resultado = market_data.buscar_cotacoes_hgbrasil(["PETR4", "VALE3"])
        assert resultado["PETR4"]["preco"] == 29.45
        assert round(resultado["PETR4"]["previousClose"], 2) == 28.95
        assert resultado["PETR4"]["fonte"] == "HG Brasil Finance"
        assert resultado["VALE3"]["preco"] == 60.10
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_cotacoes_hgbrasil_resultado_unico_como_dict_direto():
    """Formato alternativo já visto em integrações parecidas: 1 símbolo só, "results" é um único objeto (com "symbol" na raiz), não uma lista."""
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = lambda *a, **kw: _RespostaHgBrasilFalsa(200, {"results": {"symbol": "PETR4", "name": "Petrobrás", "price": 29.45}})
    try:
        resultado = market_data.buscar_cotacoes_hgbrasil(["PETR4"])
        assert resultado["PETR4"]["preco"] == 29.45
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_cotacoes_hgbrasil_status_diferente_de_200_devolve_vazio():
    """Caso comum: conta sem o plano necessário para o endpoint de cotação individual."""
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = lambda *a, **kw: _RespostaHgBrasilFalsa(402, None)
    try:
        assert market_data.buscar_cotacoes_hgbrasil(["PETR4"]) == {}
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


def test_buscar_cotacoes_hgbrasil_usa_cache_no_mesmo_conjunto_de_tickers():
    _resetar_caches_hgbrasil()
    chave_original = market_data._obter_chave_hgbrasil
    get_original = requests.get
    chamadas = {"total": 0}

    def get_fake(*a, **kw):
        chamadas["total"] += 1
        return _RespostaHgBrasilFalsa(200, {"results": [{"symbol": "PETR4", "name": "Petrobrás", "price": 29.45}]})

    market_data._obter_chave_hgbrasil = lambda: "chave-falsa"
    requests.get = get_fake
    try:
        market_data.buscar_cotacoes_hgbrasil(["PETR4"])
        market_data.buscar_cotacoes_hgbrasil(["PETR4"])
        assert chamadas["total"] == 1
    finally:
        market_data._obter_chave_hgbrasil = chave_original
        requests.get = get_original


# ==========================================================================
# _pontos_de_historico_yahoo (2026-09-03 — gráfico individual por ativo,
# aba Carteira). A busca de verdade (buscar_historico_preco) chama
# yf.Ticker(...).history(...), que depende inteiramente da rede — mesmo
# motivo de _buscar_preco_yahoo não ser testada diretamente (ver docstring
# no topo deste arquivo). Só a CONVERSÃO do resultado (DataFrame -> lista
# de pontos) tem lógica própria, então é ela que é testada aqui, com um
# objeto falso simples no lugar do DataFrame do pandas (sem precisar do
# pandas de verdade nem da rede).
# ==========================================================================

class _ColunaFalsa:
    def __init__(self, valores):
        self._valores = valores

    def tolist(self):
        return self._valores


class _HistoricoYahooFalso:
    """Dublê de um DataFrame do pandas — só o suficiente que
    _pontos_de_historico_yahoo usa: `.empty`, `.index` (iterável de objetos
    com `.strftime`, como `datetime.date` de verdade) e `["Close"].tolist()`."""

    def __init__(self, indices, fechamentos):
        self.empty = len(indices) == 0
        self.index = indices
        self._fechamentos = fechamentos

    def __getitem__(self, nome):
        assert nome == "Close"
        return _ColunaFalsa(self._fechamentos)


def test_pontos_de_historico_yahoo_caminho_feliz():
    historico = _HistoricoYahooFalso(
        [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)],
        [30.0, 30.5, 31.2],
    )
    pontos = market_data._pontos_de_historico_yahoo(historico)
    assert pontos == [
        {"data": "2026-08-01", "fechamento": 30.0},
        {"data": "2026-08-02", "fechamento": 30.5},
        {"data": "2026-08-03", "fechamento": 31.2},
    ]


def test_pontos_de_historico_yahoo_ignora_fechamento_invalido():
    """Um NaN esporádico do Yahoo (comum no primeiro pregão do período, ou
    num feriado que ainda entra no índice) não pode quebrar o gráfico
    inteiro — a linha é descartada, o resto continua normal."""
    historico = _HistoricoYahooFalso(
        [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)],
        [30.0, float("nan"), 31.2],
    )
    pontos = market_data._pontos_de_historico_yahoo(historico)
    assert pontos == [
        {"data": "2026-08-01", "fechamento": 30.0},
        {"data": "2026-08-03", "fechamento": 31.2},
    ]


def test_pontos_de_historico_yahoo_vazio_devolve_lista_vazia():
    assert market_data._pontos_de_historico_yahoo(_HistoricoYahooFalso([], [])) == []
