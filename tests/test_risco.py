"""
Testes automatizados de core/risco.py — Beta e Índice de Sharpe
aproximados da carteira, calculados a partir dos snapshots de
dados["historico"]. Módulo puro, todos os testes com números inventados
(o valor do beta em test_beta_bate_com_calculo_independente foi conferido
de forma independente com o módulo `statistics` da biblioteca padrão do
Python, não só reproduzindo a mesma fórmula deste arquivo).

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import data_store, risco


def _historico_5_pontos() -> list[dict]:
    return [
        {"data": "2024-01-01", "totalInvestido": 10000.0, "totalAtual": 10000.0, "ibov": 100000.0},
        {"data": "2024-01-02", "totalInvestido": 10000.0, "totalAtual": 10500.0, "ibov": 103000.0},
        {"data": "2024-01-03", "totalInvestido": 10000.0, "totalAtual": 10200.0, "ibov": 101000.0},
        {"data": "2024-01-04", "totalInvestido": 10000.0, "totalAtual": 10800.0, "ibov": 104500.0},
        {"data": "2024-01-05", "totalInvestido": 10000.0, "totalAtual": 10600.0, "ibov": 103500.0},
    ]


# ==========================================================================
# Beta
# ==========================================================================

def test_beta_bate_com_calculo_independente_via_statistics():
    """
    Conferido de forma independente com o módulo `statistics` da biblioteca
    padrão (não com a mesma fórmula deste arquivo):
        retornos carteira: [0.05, -0.0285714286, 0.0588235294, -0.0185185185]
        retornos ibov:      [0.03, -0.0194174757, 0.0346534653, -0.0095693780]
        beta = Cov(carteira, ibov) / Var(ibov) ≈ 1.6522607761
    """
    beta = risco.calcular_beta(_historico_5_pontos())
    assert beta == pytest.approx(1.6522607760980739, rel=1e-9)


def test_beta_none_com_menos_de_3_retornos():
    historico_curto = _historico_5_pontos()[:3]  # só 2 retornos
    assert risco.calcular_beta(historico_curto) is None


def test_beta_none_quando_ibovespa_nao_variou():
    """Variância zero no denominador -> None, nunca ZeroDivisionError."""
    historico = [
        {"data": "2024-01-01", "totalInvestido": 10000.0, "totalAtual": 10000.0, "ibov": 100000.0},
        {"data": "2024-01-02", "totalInvestido": 10000.0, "totalAtual": 10500.0, "ibov": 100000.0},
        {"data": "2024-01-03", "totalInvestido": 10000.0, "totalAtual": 10200.0, "ibov": 100000.0},
        {"data": "2024-01-04", "totalInvestido": 10000.0, "totalAtual": 10800.0, "ibov": 100000.0},
    ]
    assert risco.calcular_beta(historico) is None


def test_beta_ignora_snapshots_sem_ibovespa_registrado():
    """Snapshots antigos (de antes do Ibovespa ser salvo no histórico) não
    devem quebrar a conta — só entram os que têm 'ibov'."""
    historico = [
        {"data": "2023-01-01", "totalInvestido": 10000.0, "totalAtual": 10000.0},  # sem ibov -> ignorado
        *_historico_5_pontos(),
    ]
    beta_com_antigo = risco.calcular_beta(historico)
    beta_sem_antigo = risco.calcular_beta(_historico_5_pontos())
    assert beta_com_antigo == pytest.approx(beta_sem_antigo)


def test_beta_ignora_snapshots_duplicados_no_mesmo_dia():
    """Dois snapshots no mesmo dia (0 dias de intervalo) não formam um
    período válido e devem ser pulados, não gerar um retorno espúrio."""
    historico = _historico_5_pontos()
    historico_com_duplicata = historico[:2] + [dict(historico[1])] + historico[2:]  # repete o 2º ponto
    beta_normal = risco.calcular_beta(historico)
    beta_com_duplicata = risco.calcular_beta(historico_com_duplicata)
    assert beta_com_duplicata == pytest.approx(beta_normal)


# ==========================================================================
# Sharpe
# ==========================================================================

def test_sharpe_none_com_menos_de_3_retornos():
    assert risco.calcular_sharpe_anualizado(_historico_5_pontos()[:3], 10.0) is None


def test_sharpe_none_quando_carteira_nao_tem_nenhuma_variacao():
    """Desvio padrão zero (retorno idêntico em todos os períodos) -> None,
    nunca ZeroDivisionError."""
    historico = [
        {"data": "2024-01-01", "totalInvestido": 10000.0, "totalAtual": 10000.0, "ibov": 100000.0},
        {"data": "2024-01-02", "totalInvestido": 10000.0, "totalAtual": 10100.0, "ibov": 101000.0},
        {"data": "2024-01-03", "totalInvestido": 10000.0, "totalAtual": 10201.0, "ibov": 102000.0},
        {"data": "2024-01-04", "totalInvestido": 10000.0, "totalAtual": 10303.01, "ibov": 103000.0},
    ]
    # retorno da carteira é exatamente 1% em todos os períodos
    assert risco.calcular_sharpe_anualizado(historico, 10.0) is None


def test_sharpe_positivo_quando_retorno_supera_taxa_livre_de_risco():
    """Com uma taxa livre de risco bem baixa (1% a.a.), a carteira do
    fixture (que rende bem mais que isso) deve ter Sharpe positivo."""
    sharpe = risco.calcular_sharpe_anualizado(_historico_5_pontos(), 1.0)
    assert sharpe is not None
    assert sharpe > 0


def test_sharpe_fica_menor_quando_taxa_livre_de_risco_e_maior():
    """Aumentar a taxa livre de risco (mantendo tudo o mais igual) deve
    reduzir o Sharpe — é um retorno em excesso menor, na mesma volatilidade."""
    sharpe_taxa_baixa = risco.calcular_sharpe_anualizado(_historico_5_pontos(), 1.0)
    sharpe_taxa_alta = risco.calcular_sharpe_anualizado(_historico_5_pontos(), 50.0)
    assert sharpe_taxa_alta < sharpe_taxa_baixa


# ==========================================================================
# Ajuste por aporte/retirada (mesmo princípio de calc.twr_vs_ibovespa)
# ==========================================================================

def test_aporte_nao_conta_como_retorno_de_mercado_da_carteira():
    """
    Se o total investido dobrou (aporte) na mesma proporção que o total
    atual num dos períodos, aquele período específico deve ter retorno
    ~0%, não "a carteira dobrou de valor".
    """
    historico = [
        {"data": "2024-01-01", "totalInvestido": 10000.0, "totalAtual": 10000.0, "ibov": 100000.0},
        {"data": "2024-01-02", "totalInvestido": 20000.0, "totalAtual": 20000.0, "ibov": 101000.0},  # aporte de 10.000
        {"data": "2024-01-03", "totalInvestido": 20000.0, "totalAtual": 20200.0, "ibov": 102000.0},
        {"data": "2024-01-04", "totalInvestido": 20000.0, "totalAtual": 19800.0, "ibov": 101500.0},
    ]
    retornos_carteira, _, _ = risco._retornos_carteira_e_ibov(historico)
    assert retornos_carteira[0] == pytest.approx(0.0)


# ==========================================================================
# calcular_risco_carteira — ponto de entrada único
# ==========================================================================

def test_calcular_risco_carteira_com_dados_suficientes():
    resultado = risco.calcular_risco_carteira(_historico_5_pontos(), 10.0)
    assert resultado.beta is not None
    assert resultado.sharpe_anualizado is not None
    assert resultado.numero_periodos == 4
    assert resultado.aviso is None


def test_calcular_risco_carteira_com_dados_insuficientes_traz_aviso():
    resultado = risco.calcular_risco_carteira(_historico_5_pontos()[:3], 10.0)
    assert resultado.beta is None
    assert resultado.sharpe_anualizado is None
    assert resultado.aviso is not None
    assert "Atualizar Dados" in resultado.aviso


def test_calcular_risco_carteira_com_historico_vazio_nao_lanca_erro():
    resultado = risco.calcular_risco_carteira([], 10.0)
    assert resultado.beta is None
    assert resultado.sharpe_anualizado is None
    assert resultado.numero_periodos == 0
    assert resultado.dias_cobertos is None
    assert resultado.aviso is not None


# ==========================================================================
# Configuração persistida (dados['taxaLivreRiscoAnualPct'])
# ==========================================================================

def test_estrutura_padrao_ja_inclui_taxa_livre_de_risco_com_valor_padrao():
    """A aba Evolução lê dados['taxaLivreRiscoAnualPct'] direto — precisa
    existir desde o primeiro carregamento (carteira nova), com um valor
    numérico razoável, não None (senão o number_input do Streamlit quebra)."""
    dados = data_store.estrutura_padrao()
    assert isinstance(dados["taxaLivreRiscoAnualPct"], (int, float))
    assert dados["taxaLivreRiscoAnualPct"] > 0
