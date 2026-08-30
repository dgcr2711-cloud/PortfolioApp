"""
Testes automatizados de core/portfolio_analytics.py — concentração (HHI),
diversificação setorial, CAGR aproximado, maior perda registrada e
fundamentos ponderados pela carteira.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import portfolio_analytics as pa


# ==========================================================================
# Concentração por ativo
# ==========================================================================

def test_concentracao_por_ativo_calcula_peso_percentual_e_ordena():
    posicoes = [
        {"ticker": "PETR4", "atual": 300.0},
        {"ticker": "VALE3", "atual": 700.0},
    ]
    resultado = pa.concentracao_por_ativo(posicoes)
    assert resultado[0]["ticker"] == "VALE3"
    assert resultado[0]["peso_pct"] == pytest.approx(70.0)
    assert resultado[1]["peso_pct"] == pytest.approx(30.0)


def test_concentracao_por_ativo_lista_vazia_quando_total_zero():
    assert pa.concentracao_por_ativo([]) == []
    assert pa.concentracao_por_ativo([{"ticker": "X", "atual": 0.0}]) == []


# ==========================================================================
# Diagnóstico de concentração (HHI)
# ==========================================================================

def test_diagnostico_concentracao_lista_vazia_retorna_baixa_sem_alerta():
    diag = pa.diagnostico_concentracao([])
    assert diag.maior_ticker is None
    assert diag.classificacao_hhi == "baixa"
    assert diag.alerta_concentracao is False


def test_diagnostico_concentracao_carteira_bem_diversificada_classifica_baixa():
    # 10 ativos de 10% cada: HHI = 10 * (0.10)^2 = 0.10 -> baixa
    concentracao = [{"ticker": f"A{i}", "peso_pct": 10.0} for i in range(10)]
    diag = pa.diagnostico_concentracao(concentracao)
    assert diag.indice_hhi == pytest.approx(0.10)
    assert diag.classificacao_hhi == "baixa"
    assert diag.alerta_concentracao is False


def test_diagnostico_concentracao_moderada():
    # 5 ativos de 20% cada: HHI = 5 * 0.04 = 0.20 -> moderada
    concentracao = [{"ticker": f"A{i}", "peso_pct": 20.0} for i in range(5)]
    diag = pa.diagnostico_concentracao(concentracao)
    assert diag.classificacao_hhi == "moderada"


def test_diagnostico_concentracao_alta_e_dispara_alerta_no_maior_ativo():
    # um ativo sozinho com 60% do patrimônio -> alta concentração e alerta
    concentracao = [
        {"ticker": "PETR4", "peso_pct": 60.0},
        {"ticker": "VALE3", "peso_pct": 40.0},
    ]
    diag = pa.diagnostico_concentracao(concentracao, limite_alerta_pct=20.0)
    assert diag.maior_ticker == "PETR4"
    assert diag.maior_peso_pct == pytest.approx(60.0)
    assert diag.classificacao_hhi == "alta"
    assert diag.alerta_concentracao is True


def test_diagnostico_concentracao_nao_alerta_quando_abaixo_do_limite():
    concentracao = [{"ticker": "PETR4", "peso_pct": 15.0}, {"ticker": "VALE3", "peso_pct": 85.0}]
    diag = pa.diagnostico_concentracao([{"ticker": "PETR4", "peso_pct": 15.0}], limite_alerta_pct=20.0)
    assert diag.alerta_concentracao is False


# ==========================================================================
# Diversificação setorial
# ==========================================================================

def test_diversificacao_setorial_agrupa_valores_do_mesmo_setor():
    posicoes = [
        {"ticker": "ITUB4", "atual": 400.0},
        {"ticker": "BBAS3", "atual": 200.0},
        {"ticker": "VALE3", "atual": 400.0},
    ]
    setores = {"ITUB4": "Bancos", "BBAS3": "Bancos", "VALE3": "Mineração e Siderurgia"}
    resultado = pa.diversificacao_setorial(posicoes, setores)
    bancos = next(r for r in resultado if r["setor"] == "Bancos")
    assert bancos["valor"] == pytest.approx(600.0)
    assert bancos["peso_pct"] == pytest.approx(60.0)


def test_diversificacao_setorial_usa_rotulo_padrao_quando_sem_setor():
    posicoes = [{"ticker": "XYZ11", "atual": 100.0}]
    resultado = pa.diversificacao_setorial(posicoes, setores={})
    assert resultado[0]["setor"] == "Sem setor definido"


def test_diversificacao_setorial_vazio_quando_total_zero():
    assert pa.diversificacao_setorial([], {}) == []


# ==========================================================================
# CAGR aproximado
# ==========================================================================

def test_cagr_aproximado_none_com_menos_de_2_snapshots():
    assert pa.cagr_aproximado([]) is None
    assert pa.cagr_aproximado([{"data": "2024-01-01", "totalAtual": 1000, "totalInvestido": 1000}]) is None


def test_cagr_aproximado_none_com_periodo_menor_que_30_dias():
    historico = [
        {"data": "2024-01-01", "totalAtual": 1000.0, "totalInvestido": 1000.0},
        {"data": "2024-01-10", "totalAtual": 1100.0, "totalInvestido": 1000.0},
    ]
    assert pa.cagr_aproximado(historico) is None


def test_cagr_aproximado_anualiza_retorno_de_um_ano_exato():
    # carteira rendeu exatamente 10% em ~1 ano, sem aporte -> CAGR ~= 10%
    historico = [
        {"data": "2023-01-01", "totalAtual": 1000.0, "totalInvestido": 1000.0},
        {"data": "2024-01-01", "totalAtual": 1100.0, "totalInvestido": 1000.0},
    ]
    cagr = pa.cagr_aproximado(historico)
    assert cagr == pytest.approx(10.0, rel=0.01)


def test_cagr_aproximado_ignora_aporte_como_ganho():
    historico = [
        {"data": "2023-01-01", "totalAtual": 1000.0, "totalInvestido": 1000.0},
        {"data": "2024-01-01", "totalAtual": 2000.0, "totalInvestido": 2000.0},  # aporte, não ganho
    ]
    cagr = pa.cagr_aproximado(historico)
    assert cagr == pytest.approx(0.0, abs=0.5)


# ==========================================================================
# Maior perda registrada (drawdown simplificado)
# ==========================================================================

def test_maior_perda_registrada_none_com_menos_de_2_snapshots():
    assert pa.maior_perda_registrada([]) is None
    assert pa.maior_perda_registrada([{"totalAtual": 1000.0}]) is None


def test_maior_perda_registrada_calcula_queda_em_relacao_ao_pico():
    historico = [
        {"totalAtual": 1000.0},
        {"totalAtual": 1500.0},  # novo pico
        {"totalAtual": 1200.0},  # queda de 20% em relação ao pico de 1500
        {"totalAtual": 1400.0},  # recupera, mas não supera o pico
    ]
    pior_queda = pa.maior_perda_registrada(historico)
    assert pior_queda == pytest.approx(-20.0)


def test_maior_perda_registrada_zero_quando_so_sobe():
    historico = [{"totalAtual": 1000.0}, {"totalAtual": 1100.0}, {"totalAtual": 1300.0}]
    assert pa.maior_perda_registrada(historico) == pytest.approx(0.0)


# ==========================================================================
# Fundamentos ponderados
# ==========================================================================

def test_fundamentos_ponderados_media_ponderada_pelo_peso_no_patrimonio():
    posicoes = [
        {"ticker": "ITUB4", "atual": 300.0},
        {"ticker": "BBAS3", "atual": 700.0},
    ]
    fundamentos = {
        "ITUB4": {"pl": 10.0, "pvp": 2.0, "dividend_yield": 5.0, "roe": 20.0},
        "BBAS3": {"pl": 5.0, "pvp": 1.0, "dividend_yield": 8.0, "roe": 15.0},
    }
    resultado = pa.fundamentos_ponderados(posicoes, fundamentos)
    # P/L ponderado = 10*0.3 + 5*0.7 = 6.5
    assert resultado["pl"] == pytest.approx(6.5)
    assert resultado["cobertura_pct"] == pytest.approx(100.0)


def test_fundamentos_ponderados_ignora_ativos_sem_fundamento_na_media():
    posicoes = [
        {"ticker": "ITUB4", "atual": 500.0},
        {"ticker": "SEMFUND3", "atual": 500.0},  # sem fundamento buscado
    ]
    fundamentos = {"ITUB4": {"pl": 10.0, "pvp": None, "dividend_yield": None, "roe": None}}
    resultado = pa.fundamentos_ponderados(posicoes, fundamentos)
    # média não deve ser "diluída" pelo ativo sem dado: P/L = 10 (só ITUB4 conta)
    assert resultado["pl"] == pytest.approx(10.0)
    assert resultado["cobertura_pct"] == pytest.approx(50.0)  # só metade do patrimônio tem fundamento


def test_fundamentos_ponderados_total_zero_retorna_none_em_tudo():
    resultado = pa.fundamentos_ponderados([], {})
    assert resultado["pl"] is None
    assert resultado["cobertura_pct"] == 0.0
