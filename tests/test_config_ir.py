"""
Testes automatizados de core.config.regra_ir_vigente_em() — motor da
tabela de alíquota/isenção do IR sobre ações versionada por data (ver
TABELA_IR_ACOES em core/config.py). Ela existe para o app continuar
aplicando a regra CORRETA em vendas antigas mesmo que a Receita Federal
mude a alíquota ou o limite de isenção no futuro — sem precisar editar
nenhuma fórmula em core/calculations.py ou core/imposto_renda.py, só
acrescentar uma linha nova na tabela.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import config


# Tabela fictícia de teste — simula uma mudança de regra a partir de
# 2030-01-01, sem tocar na tabela real (TABELA_IR_ACOES).
_TABELA_TESTE = [
    {"vigente_desde": "1900-01-01", "aliquota": 0.15, "limite_isencao_mensal": 20_000.0},
    {"vigente_desde": "2030-01-01", "aliquota": 0.175, "limite_isencao_mensal": 25_000.0},
]


def test_data_antes_da_mudanca_usa_regra_antiga():
    regra = config.regra_ir_vigente_em("2029-12-31", tabela=_TABELA_TESTE)
    assert regra["aliquota"] == pytest.approx(0.15)
    assert regra["limite_isencao_mensal"] == pytest.approx(20_000.0)


def test_data_exatamente_no_dia_da_vigencia_ja_usa_regra_nova():
    regra = config.regra_ir_vigente_em("2030-01-01", tabela=_TABELA_TESTE)
    assert regra["aliquota"] == pytest.approx(0.175)
    assert regra["limite_isencao_mensal"] == pytest.approx(25_000.0)


def test_data_bem_depois_da_mudanca_usa_regra_nova():
    regra = config.regra_ir_vigente_em("2035-06-15", tabela=_TABELA_TESTE)
    assert regra["aliquota"] == pytest.approx(0.175)


def test_aceita_formato_aaaa_mm_sem_dia():
    assert config.regra_ir_vigente_em("2029-12", tabela=_TABELA_TESTE)["aliquota"] == pytest.approx(0.15)
    assert config.regra_ir_vigente_em("2030-01", tabela=_TABELA_TESTE)["aliquota"] == pytest.approx(0.175)


def test_data_vazia_ou_none_cai_na_regra_mais_antiga_sem_lancar_erro():
    assert config.regra_ir_vigente_em(None, tabela=_TABELA_TESTE)["aliquota"] == pytest.approx(0.15)
    assert config.regra_ir_vigente_em("", tabela=_TABELA_TESTE)["aliquota"] == pytest.approx(0.15)


def test_data_muito_antiga_ainda_cai_na_primeira_linha():
    assert config.regra_ir_vigente_em("1950-01-01", tabela=_TABELA_TESTE)["aliquota"] == pytest.approx(0.15)


def test_tabela_real_tem_pelo_menos_uma_linha_e_bate_com_as_constantes_de_compatibilidade():
    """ALIQUOTA_IR_ACOES/LIMITE_ISENCAO_IR_MENSAL (usadas por código antigo)
    precisam continuar batendo com a regra vigente hoje na tabela real."""
    assert len(config.TABELA_IR_ACOES) >= 1
    regra_atual = config.regra_ir_vigente_em("2026-08-30")
    assert regra_atual["aliquota"] == pytest.approx(config.ALIQUOTA_IR_ACOES)
    assert regra_atual["limite_isencao_mensal"] == pytest.approx(config.LIMITE_ISENCAO_IR_MENSAL)


def test_tabela_real_esta_ordenada_por_vigente_desde_crescente():
    """Se algum dia alguém acrescentar uma linha fora de ordem, a busca por
    data para de fazer sentido — este teste denuncia isso na hora."""
    datas = [linha["vigente_desde"] for linha in config.TABELA_IR_ACOES]
    assert datas == sorted(datas)
