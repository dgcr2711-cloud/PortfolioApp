"""
Testes automatizados de core/rebalanceamento.py — comparação entre meta de
alocação (%) e peso atual de cada ativo, com sugestão de ajuste em R$.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

from core import rebalanceamento as rebal


def _posicoes_exemplo() -> list[dict]:
    # Patrimônio total = 10.000: PETR4 = 6.000 (60%), VALE3 = 4.000 (40%)
    return [
        {"ticker": "PETR4", "atual": 6000.0},
        {"ticker": "VALE3", "atual": 4000.0},
    ]


def test_sem_metas_nao_ha_desvios():
    assert rebal.calcular_desvios(_posicoes_exemplo(), {}) == []


def test_sem_posicoes_nao_ha_desvios_mesmo_com_metas():
    assert rebal.calcular_desvios([], {"PETR4": 50.0}) == []


def test_desvio_positivo_quando_ativo_esta_acima_da_meta():
    """PETR4 está em 60% da carteira, meta é 50% -> 10 pontos percentuais
    acima -> deveria VENDER (valor_ajuste negativo)."""
    desvios = rebal.calcular_desvios(_posicoes_exemplo(), {"PETR4": 50.0, "VALE3": 50.0})
    petr4 = next(d for d in desvios if d.ticker == "PETR4")
    assert petr4.atual_pct == 60.0
    assert petr4.meta_pct == 50.0
    assert petr4.desvio_pp == 10.0
    assert petr4.valor_ajuste < 0  # precisa vender
    assert petr4.valor_alvo == 5000.0  # 50% de 10.000
    assert petr4.alerta is True  # 10pp > limiar padrão de 5pp


def test_desvio_negativo_quando_ativo_esta_abaixo_da_meta():
    desvios = rebal.calcular_desvios(_posicoes_exemplo(), {"PETR4": 50.0, "VALE3": 50.0})
    vale3 = next(d for d in desvios if d.ticker == "VALE3")
    assert vale3.atual_pct == 40.0
    assert vale3.desvio_pp == -10.0
    assert vale3.valor_ajuste > 0  # precisa comprar
    assert vale3.valor_ajuste == 1000.0  # 5.000 de meta - 4.000 atual


def test_ticker_com_meta_mas_sem_posicao_hoje_sugere_compra_total():
    """Um ticker com meta definida mas que ainda não foi comprado entra com
    atual_pct=0 e valor_ajuste igual ao valor_alvo inteiro."""
    desvios = rebal.calcular_desvios(_posicoes_exemplo(), {"ITUB4": 20.0})
    itub4 = desvios[0]
    assert itub4.ticker == "ITUB4"
    assert itub4.atual_pct == 0.0
    assert itub4.valor_alvo == 2000.0  # 20% de 10.000
    assert itub4.valor_ajuste == 2000.0


def test_ticker_sem_meta_definida_nao_aparece_no_resultado():
    """VALE3 não tem meta -> não deve gerar nenhuma linha, mesmo tendo posição."""
    desvios = rebal.calcular_desvios(_posicoes_exemplo(), {"PETR4": 50.0})
    tickers = {d.ticker for d in desvios}
    assert "VALE3" not in tickers
    assert tickers == {"PETR4"}


def test_dentro_do_limiar_nao_soa_alerta():
    """Desvio pequeno (2pp), abaixo do limiar padrão de 5pp -> sem alerta."""
    desvios = rebal.calcular_desvios(_posicoes_exemplo(), {"PETR4": 58.0, "VALE3": 42.0})
    petr4 = next(d for d in desvios if d.ticker == "PETR4")
    assert petr4.desvio_pp == 2.0
    assert petr4.alerta is False


def test_limiar_customizado_e_respeitado():
    """O mesmo desvio de 10pp que soa alerta com o limiar padrão (5pp) não
    soa mais com um limiar mais frouxo (15pp)."""
    desvios = rebal.calcular_desvios(_posicoes_exemplo(), {"PETR4": 50.0, "VALE3": 50.0}, limiar_alerta_pp=15.0)
    petr4 = next(d for d in desvios if d.ticker == "PETR4")
    assert petr4.alerta is False


def test_resultado_ordenado_pelo_maior_desvio_absoluto_primeiro():
    posicoes = [
        {"ticker": "AAA3", "atual": 5000.0},   # meta 50% -> 0pp de desvio
        {"ticker": "BBB3", "atual": 3000.0},   # meta 20% -> 10pp de desvio
        {"ticker": "CCC3", "atual": 2000.0},   # meta 30% -> -10pp de desvio (empate em módulo com BBB3)
    ]
    desvios = rebal.calcular_desvios(posicoes, {"AAA3": 50.0, "BBB3": 20.0, "CCC3": 30.0})
    assert desvios[0].ticker in ("BBB3", "CCC3")
    assert abs(desvios[0].desvio_pp) == 10.0
    assert desvios[-1].ticker == "AAA3"
    assert desvios[-1].desvio_pp == 0.0


def test_soma_metas_pct():
    assert rebal.soma_metas_pct({"PETR4": 40.0, "VALE3": 35.0}) == 75.0
    assert rebal.soma_metas_pct({}) == 0.0
