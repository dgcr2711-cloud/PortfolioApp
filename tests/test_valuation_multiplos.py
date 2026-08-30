"""
Testes automatizados de core/valuation_multiplos.py — o "football field"
de valuation (combina FCD + Número de Graham + Valor Patrimonial + múltiplo
de P/L). Módulo puro, todos os testes com números inventados.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import valuation_multiplos as vm


# ==========================================================================
# Número de Graham
# ==========================================================================

def test_numero_de_graham_com_lpa_e_vpa_positivos():
    # raiz(22.5 * 5 * 20) = raiz(2250) ≈ 47.4342
    assert vm.calcular_numero_graham(5.0, 20.0) == pytest.approx(47.4342, rel=1e-4)


def test_numero_de_graham_none_com_lpa_negativo():
    assert vm.calcular_numero_graham(-1.0, 20.0) is None


def test_numero_de_graham_none_com_vpa_negativo():
    assert vm.calcular_numero_graham(5.0, -3.0) is None


def test_numero_de_graham_none_com_lpa_ou_vpa_zero():
    assert vm.calcular_numero_graham(0.0, 20.0) is None
    assert vm.calcular_numero_graham(5.0, 0.0) is None


def test_numero_de_graham_none_com_dados_ausentes():
    assert vm.calcular_numero_graham(None, 20.0) is None
    assert vm.calcular_numero_graham(5.0, None) is None


# ==========================================================================
# Múltiplo de P/L
# ==========================================================================

def test_multiplo_de_pl_multiplica_lpa_pelo_pl_alvo():
    assert vm.calcular_valor_por_multiplo_pl(5.0, 12.0) == pytest.approx(60.0)


def test_multiplo_de_pl_none_com_lpa_negativo_ou_zero():
    assert vm.calcular_valor_por_multiplo_pl(-2.0, 12.0) is None
    assert vm.calcular_valor_por_multiplo_pl(0.0, 12.0) is None


def test_multiplo_de_pl_none_com_pl_alvo_ausente_ou_nao_positivo():
    assert vm.calcular_valor_por_multiplo_pl(5.0, None) is None
    assert vm.calcular_valor_por_multiplo_pl(5.0, 0.0) is None
    assert vm.calcular_valor_por_multiplo_pl(5.0, -8.0) is None


# ==========================================================================
# montar_football_field — combinação dos métodos
# ==========================================================================

def test_football_field_com_todos_os_metodos_disponiveis():
    resultado = vm.montar_football_field(lpa=5.0, vpa=20.0, pl_alvo=12.0, preco_teto_dcf=55.0)
    nomes = {m.nome for m in resultado.metodos}
    assert len(resultado.metodos) == 4
    assert "Fluxo de Caixa Descontado" in nomes
    assert "Número de Graham" in nomes
    assert "Valor Patrimonial por Ação" in nomes
    assert any(n.startswith("Múltiplo de P/L") for n in nomes)


def test_football_field_minimo_maximo_e_media():
    resultado = vm.montar_football_field(lpa=5.0, vpa=20.0, pl_alvo=12.0, preco_teto_dcf=55.0)
    valores = sorted(m.preco_justo for m in resultado.metodos)
    assert resultado.minimo == pytest.approx(valores[0])
    assert resultado.maximo == pytest.approx(valores[-1])
    assert resultado.media == pytest.approx(sum(valores) / len(valores))


def test_football_field_sem_nenhum_dado_fica_vazio_sem_lancar_erro():
    resultado = vm.montar_football_field(lpa=None, vpa=None)
    assert resultado.metodos == []
    assert resultado.minimo is None
    assert resultado.maximo is None
    assert resultado.media is None


def test_football_field_so_com_dcf_traz_so_um_metodo():
    resultado = vm.montar_football_field(lpa=None, vpa=None, preco_teto_dcf=42.0)
    assert len(resultado.metodos) == 1
    assert resultado.metodos[0].nome == "Fluxo de Caixa Descontado"
    assert resultado.minimo == resultado.maximo == pytest.approx(42.0)


def test_football_field_com_prejuizo_derruba_graham_e_multiplo_mas_mantem_vpa():
    """Uma empresa com prejuízo (LPA negativo) não tem Graham nem múltiplo
    de P/L válidos, mas o Valor Patrimonial continua fazendo sentido (é só
    o valor contábil, não depende do lucro)."""
    resultado = vm.montar_football_field(lpa=-2.0, vpa=15.0, pl_alvo=10.0)
    nomes = {m.nome for m in resultado.metodos}
    assert nomes == {"Valor Patrimonial por Ação"}


def test_football_field_dcf_negativo_ou_zero_e_ignorado():
    """Um FCD mal calibrado que desse preço-teto <= 0 não deveria entrar na
    faixa como se fosse um método válido."""
    resultado = vm.montar_football_field(lpa=None, vpa=None, preco_teto_dcf=0.0)
    assert resultado.metodos == []
    resultado2 = vm.montar_football_field(lpa=None, vpa=None, preco_teto_dcf=-10.0)
    assert resultado2.metodos == []


def test_rotulo_do_metodo_de_multiplo_inclui_o_pl_alvo_informado():
    resultado = vm.montar_football_field(lpa=5.0, vpa=None, pl_alvo=15.0)
    assert resultado.metodos[0].nome == "Múltiplo de P/L (15x)"
