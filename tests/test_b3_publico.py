"""
Testes automatizados de core/b3_publico.py — a busca de proventos direto
no site oficial da B3 (ver docstring do módulo para o contexto completo).

`requests` já está disponível de verdade neste sandbox (ao contrário de
streamlit/yfinance), então aqui não é preciso injetar um módulo falso em
sys.modules — as funções que fazem rede de verdade são testadas trocando
`requests.get` por um dublê só dentro de cada teste (sempre restaurado no
finally, mesmo padrão de "trocar e restaurar" já usado em
tests/test_notificacoes_whatsapp.py e tests/test_notificacoes_email.py).

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

from datetime import date, datetime

import requests

from core import b3_publico


# ==========================================================================
# extrair_prefixo_ticker / _montar_url
# ==========================================================================

def test_extrair_prefixo_ticker_remove_o_numero_final():
    assert b3_publico.extrair_prefixo_ticker("PETR4") == "PETR"
    assert b3_publico.extrair_prefixo_ticker("klbn4") == "KLBN"
    assert b3_publico.extrair_prefixo_ticker("  vale3  ") == "VALE"


def test_montar_url_usa_o_prefixo_certo_em_base64():
    url = b3_publico._montar_url("PETR4")
    assert url.startswith(b3_publico._URL_BASE)
    # mesmo parâmetro observado de verdade no site da B3 para PETR4
    assert url.endswith("eyJpc3N1aW5nQ29tcGFueSI6IlBFVFIiLCJsYW5ndWFnZSI6InB0LWJyIn0=")


# ==========================================================================
# _parsear_valor_br
# ==========================================================================

def test_parsear_valor_br_formato_simples():
    assert b3_publico._parsear_valor_br("0,47156696000") == 0.47156696

def test_parsear_valor_br_com_separador_de_milhar():
    assert b3_publico._parsear_valor_br("1.222.000,50") == 1222000.5

def test_parsear_valor_br_invalido_vira_none():
    assert b3_publico._parsear_valor_br(None) is None
    assert b3_publico._parsear_valor_br("") is None
    assert b3_publico._parsear_valor_br("não é número") is None


# ==========================================================================
# _parsear_data_br
# ==========================================================================

def test_parsear_data_br_formato_valido():
    assert b3_publico._parsear_data_br("21/12/2026") == "2026-12-21"

def test_parsear_data_br_data_sem_fim_vira_none():
    assert b3_publico._parsear_data_br("31/12/9999") is None

def test_parsear_data_br_invalido_vira_none():
    assert b3_publico._parsear_data_br(None) is None
    assert b3_publico._parsear_data_br("") is None
    assert b3_publico._parsear_data_br("2026-12-21") is None  # formato errado (não é dd/mm/aaaa)


# ==========================================================================
# _parsear_cash_dividends
# ==========================================================================

_RESPOSTA_EXEMPLO = [{
    "code": "PETR",
    "cashDividends": [
        {"paymentDate": "21/12/2026", "rate": "0,47156696000", "label": "DIVIDENDO",
         "relatedTo": "Anual/2026", "approvedOn": "06/08/2026", "lastDatePrior": "21/08/2026"},
        {"paymentDate": "23/11/2026", "rate": "0,67407131000", "label": "JRS CAP PROPRIO",
         "relatedTo": "Anual/2026", "approvedOn": "06/08/2026", "lastDatePrior": "21/08/2026"},
        {"paymentDate": "20/05/2026", "rate": "0,01649003000", "label": "RENDIMENTO",
         "relatedTo": "Anual/2025", "approvedOn": "16/04/2026", "lastDatePrior": "22/04/2026"},
    ],
    "stockDividends": [
        {"factor": "100,00000000000", "label": "DESDOBRAMENTO", "approvedOn": "25/04/2008"},
    ],
    "subscriptions": [
        {"label": "SUBSCRICAO", "approvedOn": "15/08/1974"},
    ],
}]


def test_parsear_cash_dividends_mapeia_os_tres_tipos():
    resultado = b3_publico._parsear_cash_dividends(_RESPOSTA_EXEMPLO, "PETR4")
    tipos = {p["tipo"] for p in resultado}
    assert tipos == {"Dividendo", "JCP", "Rendimento"}


def test_parsear_cash_dividends_ignora_stockDividends_e_subscriptions():
    resultado = b3_publico._parsear_cash_dividends(_RESPOSTA_EXEMPLO, "PETR4")
    assert len(resultado) == 3  # só os 3 cashDividends, nada de bonificação/subscrição


def test_parsear_cash_dividends_ordena_por_data_de_pagamento():
    resultado = b3_publico._parsear_cash_dividends(_RESPOSTA_EXEMPLO, "PETR4")
    assert [p["data_pagamento"] for p in resultado] == ["2026-05-20", "2026-11-23", "2026-12-21"]


def test_parsear_cash_dividends_campos_do_primeiro_item():
    resultado = b3_publico._parsear_cash_dividends(_RESPOSTA_EXEMPLO, "PETR4")
    primeiro = resultado[0]
    assert primeiro["ticker"] == "PETR4"
    assert primeiro["tipo"] == "Rendimento"
    assert primeiro["valor_por_acao"] == 0.01649003
    assert primeiro["data_com"] == "2026-04-22"
    assert primeiro["relacionado_a"] == "Anual/2025"


def test_parsear_cash_dividends_ignora_label_desconhecido():
    payload = [{"cashDividends": [
        {"paymentDate": "21/12/2026", "rate": "1,00", "label": "ALGO_NOVO_DA_B3"},
    ]}]
    assert b3_publico._parsear_cash_dividends(payload, "PETR4") == []


def test_parsear_cash_dividends_ignora_entrada_sem_data_ou_valor():
    payload = [{"cashDividends": [
        {"paymentDate": None, "rate": "1,00", "label": "DIVIDENDO"},
        {"paymentDate": "21/12/2026", "rate": None, "label": "DIVIDENDO"},
    ]}]
    assert b3_publico._parsear_cash_dividends(payload, "PETR4") == []


def test_parsear_cash_dividends_lista_vazia_quando_empresa_nao_encontrada():
    assert b3_publico._parsear_cash_dividends([], "PETR4") == []
    assert b3_publico._parsear_cash_dividends(None, "PETR4") == []
    assert b3_publico._parsear_cash_dividends({}, "PETR4") == []


# ==========================================================================
# buscar_proventos_anunciados — troca requests.get por um dublê
# ==========================================================================

class _RespostaFalsa:
    def __init__(self, status_code=200, corpo=None, lanca_no_json=False):
        self.status_code = status_code
        self._corpo = corpo
        self._lanca_no_json = lanca_no_json

    def json(self):
        if self._lanca_no_json:
            raise ValueError("corpo não é JSON válido")
        return self._corpo


def test_buscar_proventos_anunciados_caminho_feliz():
    original = requests.get
    requests.get = lambda *a, **kw: _RespostaFalsa(200, _RESPOSTA_EXEMPLO)
    try:
        resultado = b3_publico.buscar_proventos_anunciados("PETR4")
        assert len(resultado) == 3
    finally:
        requests.get = original


def test_buscar_proventos_anunciados_status_diferente_de_200_vira_lista_vazia():
    original = requests.get
    requests.get = lambda *a, **kw: _RespostaFalsa(403, None)
    try:
        assert b3_publico.buscar_proventos_anunciados("PETR4") == []
    finally:
        requests.get = original


def test_buscar_proventos_anunciados_erro_de_rede_vira_lista_vazia():
    original = requests.get
    def levanta(*a, **kw):
        raise requests.exceptions.ConnectionError("sem internet (simulado)")
    requests.get = levanta
    try:
        assert b3_publico.buscar_proventos_anunciados("PETR4") == []
    finally:
        requests.get = original


def test_buscar_proventos_anunciados_json_invalido_vira_lista_vazia():
    original = requests.get
    requests.get = lambda *a, **kw: _RespostaFalsa(200, None, lanca_no_json=True)
    try:
        assert b3_publico.buscar_proventos_anunciados("PETR4") == []
    finally:
        requests.get = original


def test_buscar_proventos_anunciados_varios_so_inclui_tickers_com_resultado():
    original = b3_publico._buscar_json_bruto
    respostas = {
        "PETR4": (True, [{"cashDividends": [
            {"paymentDate": "21/12/2026", "rate": "1,00", "label": "DIVIDENDO"},
        ]}]),
        "VALE3": (True, [{"cashDividends": []}]),
    }
    b3_publico._buscar_json_bruto = lambda ticker: respostas[ticker]
    try:
        resultado, sem_conexao = b3_publico.buscar_proventos_anunciados_varios(["PETR4", "VALE3"])
        assert list(resultado.keys()) == ["PETR4"]
        assert sem_conexao is False
    finally:
        b3_publico._buscar_json_bruto = original


def test_buscar_proventos_anunciados_varios_sem_conexao_quando_tudo_falha():
    original = b3_publico._buscar_json_bruto
    b3_publico._buscar_json_bruto = lambda ticker: (False, None)
    try:
        resultado, sem_conexao = b3_publico.buscar_proventos_anunciados_varios(["PETR4", "VALE3"])
        assert resultado == {}
        assert sem_conexao is True
    finally:
        b3_publico._buscar_json_bruto = original


def test_buscar_proventos_anunciados_varios_nao_e_sem_conexao_se_ao_menos_um_respondeu():
    original = b3_publico._buscar_json_bruto
    respostas = {"PETR4": (False, None), "VALE3": (True, [{"cashDividends": []}])}
    b3_publico._buscar_json_bruto = lambda ticker: respostas[ticker]
    try:
        _, sem_conexao = b3_publico.buscar_proventos_anunciados_varios(["PETR4", "VALE3"])
        assert sem_conexao is False
    finally:
        b3_publico._buscar_json_bruto = original


def test_buscar_proventos_anunciados_varios_lista_vazia_nao_e_sem_conexao():
    resultado, sem_conexao = b3_publico.buscar_proventos_anunciados_varios([])
    assert resultado == {}
    assert sem_conexao is False


# ==========================================================================
# proximos_a_partir_de
# ==========================================================================

def test_proximos_a_partir_de_filtra_datas_passadas():
    anunciados = {
        "PETR4": [
            {"ticker": "PETR4", "data_pagamento": "2026-01-01"},
            {"ticker": "PETR4", "data_pagamento": "2026-12-21"},
        ],
    }
    resultado = b3_publico.proximos_a_partir_de(anunciados, hoje=date(2026, 8, 31))
    assert [p["data_pagamento"] for p in resultado] == ["2026-12-21"]


def test_proximos_a_partir_de_inclui_a_data_de_hoje():
    anunciados = {"PETR4": [{"ticker": "PETR4", "data_pagamento": "2026-08-31"}]}
    resultado = b3_publico.proximos_a_partir_de(anunciados, hoje=date(2026, 8, 31))
    assert len(resultado) == 1


def test_proximos_a_partir_de_ordena_por_data_entre_tickers_diferentes():
    anunciados = {
        "PETR4": [{"ticker": "PETR4", "data_pagamento": "2026-12-21"}],
        "VALE3": [{"ticker": "VALE3", "data_pagamento": "2026-09-02"}],
    }
    resultado = b3_publico.proximos_a_partir_de(anunciados, hoje=date(2026, 8, 31))
    assert [p["ticker"] for p in resultado] == ["VALE3", "PETR4"]


def test_proximos_a_partir_de_vazio_sem_anunciados():
    assert b3_publico.proximos_a_partir_de({}, hoje=date(2026, 8, 31)) == []


# ==========================================================================
# precisa_atualizar
# ==========================================================================

def test_precisa_atualizar_true_quando_nunca_atualizou():
    assert b3_publico.precisa_atualizar(None, datetime(2026, 8, 31, 12, 0), 86400) is True
    assert b3_publico.precisa_atualizar("", datetime(2026, 8, 31, 12, 0), 86400) is True


def test_precisa_atualizar_true_quando_valor_invalido():
    assert b3_publico.precisa_atualizar("não é uma data", datetime(2026, 8, 31, 12, 0), 86400) is True


def test_precisa_atualizar_false_dentro_do_intervalo():
    agora = datetime(2026, 8, 31, 12, 0)
    atualizado_em = datetime(2026, 8, 31, 6, 0).isoformat()  # 6h atrás
    assert b3_publico.precisa_atualizar(atualizado_em, agora, intervalo_segundos=86400) is False


def test_precisa_atualizar_true_apos_o_intervalo():
    agora = datetime(2026, 8, 31, 12, 0)
    atualizado_em = datetime(2026, 8, 29, 12, 0).isoformat()  # 2 dias atrás
    assert b3_publico.precisa_atualizar(atualizado_em, agora, intervalo_segundos=86400) is True


def test_precisa_atualizar_limite_exato_conta_como_precisa():
    agora = datetime(2026, 8, 31, 12, 0)
    atualizado_em = datetime(2026, 8, 30, 12, 0).isoformat()  # exatamente 86400s atrás
    assert b3_publico.precisa_atualizar(atualizado_em, agora, intervalo_segundos=86400) is True


# ==========================================================================
# meses_anunciados_por_ticker
# ==========================================================================

def test_meses_anunciados_por_ticker_extrai_meses_unicos_ordenados():
    anunciados = {
        "PETR4": [
            {"data_pagamento": "2026-12-21"},
            {"data_pagamento": "2026-03-20"},
            {"data_pagamento": "2026-03-20"},  # duplicado (mesmo mês, dois lançamentos no mesmo dia)
        ],
    }
    resultado = b3_publico.meses_anunciados_por_ticker(anunciados)
    assert resultado == {"PETR4": [3, 12]}


def test_meses_anunciados_por_ticker_ignora_ticker_sem_dados():
    assert b3_publico.meses_anunciados_por_ticker({"PETR4": []}) == {}


def test_meses_anunciados_por_ticker_data_minima_filtra_pagamentos_antigos():
    anunciados = {
        "PETR4": [
            {"data_pagamento": "2025-11-20"},  # antes do corte
            {"data_pagamento": "2026-03-01"},  # exatamente no corte
            {"data_pagamento": "2026-09-02"},
        ],
    }
    resultado = b3_publico.meses_anunciados_por_ticker(anunciados, data_minima="2026-03-01")
    assert resultado == {"PETR4": [3, 9]}


def test_meses_anunciados_por_ticker_data_minima_pode_esvaziar_um_ticker():
    anunciados = {"PETR4": [{"data_pagamento": "2025-06-01"}]}
    resultado = b3_publico.meses_anunciados_por_ticker(anunciados, data_minima="2026-03-01")
    assert resultado == {}  # ticker inteiro some do mapa, não sobra chave vazia


def test_meses_anunciados_por_ticker_data_minima_none_nao_filtra_nada():
    anunciados = {"PETR4": [{"data_pagamento": "2020-01-01"}]}
    assert b3_publico.meses_anunciados_por_ticker(anunciados, data_minima=None) == {"PETR4": [1]}
