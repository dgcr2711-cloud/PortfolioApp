"""
Testes automatizados de core/teses.py — o diário de tese de investimento
(adicionar entrada, listar, remover).

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import data_store
from core import teses


def _dados_vazios():
    return data_store.estrutura_padrao()


def test_estrutura_padrao_ja_inclui_teses_vazio():
    dados = _dados_vazios()
    assert dados["teses"] == {}


def test_adicionar_entrada_cria_a_lista_do_ticker_se_nao_existir():
    dados = _dados_vazios()
    entrada = teses.adicionar_entrada(dados, "petr4", "Empresa sólida, dividendos consistentes.")
    assert entrada["texto"] == "Empresa sólida, dividendos consistentes."
    assert "id" in entrada and "data" in entrada
    assert dados["teses"]["PETR4"] == [entrada]  # normaliza o ticker para maiúsculo


def test_adicionar_entrada_nao_sobrescreve_a_anterior():
    dados = _dados_vazios()
    teses.adicionar_entrada(dados, "VALE3", "Primeira impressão: preço atrativo vs. Preço Teto.")
    teses.adicionar_entrada(dados, "VALE3", "Seis meses depois: tese ainda de pé, aumentei posição.")
    assert len(dados["teses"]["VALE3"]) == 2


def test_adicionar_entrada_com_texto_vazio_lanca_erro():
    dados = _dados_vazios()
    with pytest.raises(ValueError):
        teses.adicionar_entrada(dados, "ITUB4", "   ")


def test_adicionar_entrada_com_texto_longo_demais_lanca_erro():
    dados = _dados_vazios()
    texto_longo = "a" * (teses.LIMITE_CARACTERES_TEXTO + 1)
    with pytest.raises(ValueError):
        teses.adicionar_entrada(dados, "ITUB4", texto_longo)


def test_adicionar_entrada_sem_ticker_lanca_erro():
    dados = _dados_vazios()
    with pytest.raises(ValueError):
        teses.adicionar_entrada(dados, "   ", "Texto válido")


def test_listar_entradas_retorna_mais_recente_primeiro():
    dados = _dados_vazios()
    primeira = teses.adicionar_entrada(dados, "WEGE3", "Entrada mais antiga")
    segunda = teses.adicionar_entrada(dados, "WEGE3", "Entrada mais nova")
    lista = teses.listar_entradas(dados, "wege3")  # minúsculo também funciona
    assert [e["id"] for e in lista] == [segunda["id"], primeira["id"]]


def test_listar_entradas_de_ticker_sem_nenhuma_retorna_lista_vazia():
    dados = _dados_vazios()
    assert teses.listar_entradas(dados, "XPTO11") == []


def test_remover_entrada_remove_apenas_a_escolhida():
    dados = _dados_vazios()
    primeira = teses.adicionar_entrada(dados, "BBAS3", "Nota 1")
    segunda = teses.adicionar_entrada(dados, "BBAS3", "Nota 2")
    removeu = teses.remover_entrada(dados, "BBAS3", primeira["id"])
    assert removeu is True
    restantes = teses.listar_entradas(dados, "BBAS3")
    assert len(restantes) == 1
    assert restantes[0]["id"] == segunda["id"]


def test_remover_entrada_inexistente_retorna_false_sem_quebrar():
    dados = _dados_vazios()
    teses.adicionar_entrada(dados, "BBAS3", "Nota 1")
    removeu = teses.remover_entrada(dados, "BBAS3", "id-que-nao-existe")
    assert removeu is False
    assert len(teses.listar_entradas(dados, "BBAS3")) == 1


def test_remover_entrada_de_ticker_sem_nenhuma_tese_nao_quebra():
    dados = _dados_vazios()
    assert teses.remover_entrada(dados, "NUNCA11", "qualquer-id") is False


def test_tickers_com_tese_ignora_tickers_sem_entradas():
    dados = _dados_vazios()
    teses.adicionar_entrada(dados, "ITSA4", "Nota")
    teses.adicionar_entrada(dados, "KLBN4", "Nota")
    dados["teses"]["VAZIO3"] = []  # simula um ticker que ficou com lista vazia (ex: removeu tudo)
    assert teses.tickers_com_tese(dados) == ["ITSA4", "KLBN4"]
