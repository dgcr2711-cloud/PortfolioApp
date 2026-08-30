"""
Testes automatizados de core/setores.py — unificação das duas fontes de
setor (Yahoo Finance x definido manualmente na aba Carteira).

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

from core import setores
from core.config import SETORES_PADRAO


def test_sugerir_setor_traduz_setores_conhecidos_do_yahoo():
    assert setores.sugerir_setor_a_partir_do_yahoo("Energy") == "Petróleo e Gás"
    assert setores.sugerir_setor_a_partir_do_yahoo("Financial Services") == "Bancos"
    assert setores.sugerir_setor_a_partir_do_yahoo("Technology") == "Tecnologia"
    assert setores.sugerir_setor_a_partir_do_yahoo("Real Estate") == "Imobiliário"
    assert setores.sugerir_setor_a_partir_do_yahoo("Utilities") == "Energia Elétrica/Saneamento"


def test_sugerir_setor_e_insensivel_a_maiusculas_minusculas():
    assert setores.sugerir_setor_a_partir_do_yahoo("ENERGY") == "Petróleo e Gás"
    assert setores.sugerir_setor_a_partir_do_yahoo("energy") == "Petróleo e Gás"


def test_sugerir_setor_none_para_vazio_ou_desconhecido():
    assert setores.sugerir_setor_a_partir_do_yahoo(None) is None
    assert setores.sugerir_setor_a_partir_do_yahoo("") is None
    assert setores.sugerir_setor_a_partir_do_yahoo("Setor Que Não Existe No Yahoo De Verdade") is None


def test_todas_as_sugestoes_sao_categorias_validas_de_setores_padrao():
    """Nenhuma sugestão pode apontar para um rótulo que não existe em SETORES_PADRAO
    (ex: um erro de digitação no mapa quebraria o seletor da aba Carteira)."""
    for setor_yahoo in setores._MAPA_SETOR_YAHOO_PARA_PADRAO:
        sugestao = setores.sugerir_setor_a_partir_do_yahoo(setor_yahoo)
        assert sugestao in SETORES_PADRAO, f"{setor_yahoo!r} sugere {sugestao!r}, que não está em SETORES_PADRAO"


def test_preencher_setores_sugeridos_preenche_apenas_quem_nao_tem_setor():
    dados = {
        "setores": {"PETR4": "Petróleo e Gás"},  # já tem setor manual — não deve mudar
        "fundamentos": {
            "PETR4": {"setor_yahoo": "Financial Services"},  # divergente de propósito: nunca deve sobrescrever
            "VALE3": {"setor_yahoo": "Basic Materials"},  # sem setor ainda — deve ser preenchido
            "WEGE3": {"setor_yahoo": None},  # sem dado do Yahoo — não preenche nada
        },
    }
    preenchidos = setores.preencher_setores_sugeridos(dados)
    assert preenchidos == 1
    assert dados["setores"]["PETR4"] == "Petróleo e Gás"  # não foi sobrescrito
    assert dados["setores"]["VALE3"] == "Mineração e Siderurgia"
    assert "WEGE3" not in dados["setores"]


def test_preencher_setores_sugeridos_nunca_sobrescreve_setor_manual_mesmo_que_pareca_diferente():
    dados = {
        "setores": {"ITUB4": "Outros"},  # escolha manual "estranha", mas é a escolha do usuário
        "fundamentos": {"ITUB4": {"setor_yahoo": "Financial Services"}},
    }
    preenchidos = setores.preencher_setores_sugeridos(dados)
    assert preenchidos == 0
    assert dados["setores"]["ITUB4"] == "Outros"


def test_preencher_setores_sugeridos_com_dados_vazios_nao_quebra():
    dados = {}
    assert setores.preencher_setores_sugeridos(dados) == 0
    assert dados["setores"] == {}
