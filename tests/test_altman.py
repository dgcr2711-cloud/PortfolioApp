"""
Testes automatizados de core/altman.py — o cálculo puro do Altman Z-Score.
Como o módulo não fala com o Yahoo Finance, todos os testes usam números
inventados, com o Z conferido na mão (a conta está em cada docstring).

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import altman


def test_empresa_solida_cai_na_zona_segura():
    """
    A=0.3, B=0.4, C=0.2, D=5.0, E=1.2
    Z = 1.2*0.3 + 1.4*0.4 + 3.3*0.2 + 0.6*5.0 + 1.0*1.2
      = 0.36 + 0.56 + 0.66 + 3.0 + 1.2 = 5.78 -> bem acima de 2.99
    """
    dados = {
        "ativo_circulante": 5_000_000.0, "passivo_circulante": 2_000_000.0,  # capital de giro 3.000.000
        "ativos_totais": 10_000_000.0,
        "lucros_retidos": 4_000_000.0,
        "ebit": 2_000_000.0,
        "valor_mercado": 15_000_000.0, "passivo_total": 3_000_000.0,
        "receita": 12_000_000.0,
    }
    resultado = altman.calcular_altman(dados)
    assert resultado.z_score == pytest.approx(5.78)
    assert resultado.classificacao == "Zona Segura"


def test_empresa_em_dificuldade_cai_na_zona_de_risco():
    """
    A=-0.1, B=-0.05, C=-0.02, D=0.125, E=0.5
    Z = 1.2*(-0.1) + 1.4*(-0.05) + 3.3*(-0.02) + 0.6*0.125 + 1.0*0.5
      = -0.12 - 0.07 - 0.066 + 0.075 + 0.5 = 0.319 -> bem abaixo de 1.81
    """
    dados = {
        "ativo_circulante": 1_000_000.0, "passivo_circulante": 2_000_000.0,  # capital de giro NEGATIVO
        "ativos_totais": 10_000_000.0,
        "lucros_retidos": -500_000.0,  # prejuízos acumulados
        "ebit": -200_000.0,
        "valor_mercado": 1_000_000.0, "passivo_total": 8_000_000.0,
        "receita": 5_000_000.0,
    }
    resultado = altman.calcular_altman(dados)
    assert resultado.z_score == pytest.approx(0.319)
    assert resultado.classificacao == "Zona de Risco"


def test_empresa_no_meio_cai_na_zona_de_alerta():
    """
    A=B=C=E=0.2, D=1.0
    Z = 1.2*0.2 + 1.4*0.2 + 3.3*0.2 + 0.6*1.0 + 1.0*0.2
      = 0.24 + 0.28 + 0.66 + 0.6 + 0.2 = 1.98 -> entre 1.81 e 2.99
    """
    dados = {
        "ativo_circulante": 3_000_000.0, "passivo_circulante": 1_000_000.0,  # capital de giro 2.000.000 -> A=0.2
        "ativos_totais": 10_000_000.0,
        "lucros_retidos": 2_000_000.0,  # B=0.2
        "ebit": 2_000_000.0,  # C=0.2
        "valor_mercado": 5_000_000.0, "passivo_total": 5_000_000.0,  # D=1.0
        "receita": 2_000_000.0,  # E=0.2
    }
    resultado = altman.calcular_altman(dados)
    assert resultado.z_score == pytest.approx(1.98)
    assert resultado.classificacao == "Zona de Alerta"


def test_limiar_exato_2_99_ainda_e_zona_de_alerta_nao_segura():
    """A fronteira >2.99 exige valor ESTRITAMENTE maior — exatamente 2.99 cai
    do lado "de alerta", não "seguro"."""
    # Escolhido pra fechar Z = 2.99 exatamente: A=B=C=D=E=x -> Z = 7.5x
    x = 2.99 / 7.5
    dados = {
        "ativo_circulante": x * 10_000_000.0, "passivo_circulante": 0.0,
        "ativos_totais": 10_000_000.0,
        "lucros_retidos": x * 10_000_000.0,
        "ebit": x * 10_000_000.0,
        "valor_mercado": x * 10_000_000.0, "passivo_total": 10_000_000.0,
        "receita": x * 10_000_000.0,
    }
    resultado = altman.calcular_altman(dados)
    assert resultado.z_score == pytest.approx(2.99)
    assert resultado.classificacao == "Zona de Alerta"


def test_limiar_exato_1_81_ja_e_zona_de_alerta_nao_de_risco():
    """A fronteira de baixo é INCLUSIVA (>=1.81 já é alerta, não risco)."""
    x = 1.81 / 7.5
    dados = {
        "ativo_circulante": x * 10_000_000.0, "passivo_circulante": 0.0,
        "ativos_totais": 10_000_000.0,
        "lucros_retidos": x * 10_000_000.0,
        "ebit": x * 10_000_000.0,
        "valor_mercado": x * 10_000_000.0, "passivo_total": 10_000_000.0,
        "receita": x * 10_000_000.0,
    }
    resultado = altman.calcular_altman(dados)
    assert resultado.z_score == pytest.approx(1.81)
    assert resultado.classificacao == "Zona de Alerta"


def test_dicionario_vazio_nao_calcula_e_nao_lanca_erro():
    resultado = altman.calcular_altman({})
    assert resultado.z_score is None
    assert resultado.classificacao == "Dados insuficientes"
    assert all(v is None for v in resultado.componentes.values())


def test_faltando_um_unico_campo_impede_o_calculo_do_z_final():
    """Diferente do Piotroski (que dá crédito parcial), o Altman precisa dos
    5 componentes — faltando só o EBIT, o Z final já não sai."""
    dados = {
        "ativo_circulante": 5_000_000.0, "passivo_circulante": 2_000_000.0,
        "ativos_totais": 10_000_000.0,
        "lucros_retidos": 4_000_000.0,
        # "ebit" ausente de propósito
        "valor_mercado": 15_000_000.0, "passivo_total": 3_000_000.0,
        "receita": 12_000_000.0,
    }
    resultado = altman.calcular_altman(dados)
    assert resultado.z_score is None
    assert resultado.classificacao == "Dados insuficientes"
    # mas os componentes que DERAM pra calcular continuam disponíveis —
    # útil pra mostrar ao usuário qual dado específico está faltando
    assert resultado.componentes["capital_giro_sobre_ativos"] == pytest.approx(0.3)
    assert resultado.componentes["ebit_sobre_ativos"] is None


def test_passivo_total_zero_nao_quebra_vira_componente_nao_avaliado():
    dados = {
        "ativo_circulante": 5_000_000.0, "passivo_circulante": 2_000_000.0,
        "ativos_totais": 10_000_000.0,
        "lucros_retidos": 4_000_000.0,
        "ebit": 2_000_000.0,
        "valor_mercado": 15_000_000.0, "passivo_total": 0.0,  # divisão por zero
        "receita": 12_000_000.0,
    }
    resultado = altman.calcular_altman(dados)
    assert resultado.z_score is None
    assert resultado.componentes["valor_mercado_sobre_passivo"] is None
