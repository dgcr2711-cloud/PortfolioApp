"""
Testes automatizados de core/imposto_renda.py — a parte mais delicada do
motor de cálculo: separação automática de Day Trade vs. Swing Trade,
compensação de prejuízo mês a mês, e a regra do DARF mínimo de R$10.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import imposto_renda as ir


# ==========================================================================
# Separação Day Trade vs. Swing Trade
# ==========================================================================

def test_separa_day_trade_quando_compra_e_venda_no_mesmo_dia_mesmo_ticker():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "PETR4", "data": "2024-05-10", "qtd": 100, "preco": 30.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "PETR4", "data": "2024-05-10", "qtd": 100, "preco": 32.0, "taxas": 0.0},
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    assert len(resultado.day_trade) == 1
    assert resultado.day_trade[0]["qtd"] == pytest.approx(100.0)
    assert resultado.day_trade[0]["lucro"] == pytest.approx(200.0)  # 100 * (32-30)
    assert resultado.swing == []  # tudo foi day trade, nada sobrou pro swing


def test_day_trade_pega_apenas_o_menor_entre_comprado_e_vendido_no_dia():
    """
    Comprou 150 e vendeu 100 no mesmo dia: 100 é day trade (o menor dos
    dois); as 50 restantes da compra seguem para o ledger normal (swing),
    mantendo posição em aberto.
    """
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "VALE3", "data": "2024-05-10", "qtd": 150, "preco": 60.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "VALE3", "data": "2024-05-10", "qtd": 100, "preco": 65.0, "taxas": 0.0},
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    assert len(resultado.day_trade) == 1
    assert resultado.day_trade[0]["qtd"] == pytest.approx(100.0)
    # sobra posição de 50 ações compradas a 60, sem venda associada -> nenhum resultado de swing ainda
    assert resultado.swing == []


def test_sem_day_trade_quando_so_compra_ou_so_venda_no_dia():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "ITUB4", "data": "2024-05-10", "qtd": 100, "preco": 30.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "ITUB4", "data": "2024-06-10", "qtd": 100, "preco": 35.0, "taxas": 0.0},
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    assert resultado.day_trade == []
    assert len(resultado.swing) == 1
    assert resultado.swing[0]["lucro"] == pytest.approx(500.0)


def test_sem_day_trade_quando_compra_e_venda_no_mesmo_dia_mas_tickers_diferentes():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "PETR4", "data": "2024-05-10", "qtd": 100, "preco": 30.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "VALE3", "data": "2024-05-10", "qtd": 100, "preco": 32.0, "taxas": 0.0},
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    assert resultado.day_trade == []


# ==========================================================================
# Resumo mensal: isenção, tributação e compensação de prejuízo (Swing)
# ==========================================================================

def test_resumo_mensal_isento_ate_20_mil_vendidos_no_mes():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "ITUB4", "data": "2024-01-01", "qtd": 1000, "preco": 10.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "ITUB4", "data": "2024-02-10", "qtd": 500, "preco": 15.0, "taxas": 0.0},  # vendeu 7.500
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    linhas = ir.resumo_mensal_ir(resultado)
    assert len(linhas) == 1
    assert linhas[0]["swing"]["isento"] is True
    assert linhas[0]["darf_a_pagar"] == pytest.approx(0.0)


def test_resumo_mensal_tributa_15_por_cento_acima_de_20_mil_descontando_irrf():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "ITUB4", "data": "2024-01-01", "qtd": 10000, "preco": 10.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "ITUB4", "data": "2024-02-10", "qtd": 3000, "preco": 15.0, "taxas": 0.0},  # vendeu 45.000, lucro 15.000
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    linha = ir.resumo_mensal_ir(resultado)[0]
    assert linha["swing"]["isento"] is False
    imposto_bruto = 15000.0 * 0.15  # 2250
    irrf = 45000.0 * 0.00005  # 2.25
    assert linha["swing"]["imposto"] == pytest.approx(imposto_bruto)
    assert linha["swing"]["irrf_estimado"] == pytest.approx(irrf)
    assert linha["darf_a_pagar"] == pytest.approx(imposto_bruto - irrf)


def test_resumo_mensal_compensa_prejuizo_de_mes_anterior_no_swing():
    compras = [
        # mês 1: prejuízo de 5.000 (vendeu tudo com perda, valor vendido > 20k pra não cair em isenção que mascare o teste)
        {"id": "1", "tipo": "compra", "ticker": "MGLU3", "data": "2024-01-01", "qtd": 10000, "preco": 5.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "MGLU3", "data": "2024-01-15", "qtd": 10000, "preco": 4.5, "taxas": 0.0},  # -5000
        # mês 2: lucro de 8.000 sobre outro lote
        {"id": "3", "tipo": "compra", "ticker": "MGLU3", "data": "2024-02-01", "qtd": 10000, "preco": 5.0, "taxas": 0.0},
        {"id": "4", "tipo": "venda", "ticker": "MGLU3", "data": "2024-02-15", "qtd": 10000, "preco": 5.8, "taxas": 0.0},  # +8000
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    linhas = ir.resumo_mensal_ir(resultado)
    mes1 = next(l for l in linhas if l["mes"] == "2024-01")
    mes2 = next(l for l in linhas if l["mes"] == "2024-02")

    assert mes1["swing"]["lucro"] == pytest.approx(-5000.0)
    assert mes1["swing"]["prejuizo_acumulado_restante"] == pytest.approx(5000.0)
    assert mes1["darf_a_pagar"] == pytest.approx(0.0)

    # mês 2: lucro de 8000, compensa os 5000 de prejuízo -> tributa só 3000
    assert mes2["swing"]["prejuizo_compensado"] == pytest.approx(5000.0)
    assert mes2["swing"]["prejuizo_acumulado_restante"] == pytest.approx(0.0)
    assert mes2["swing"]["imposto"] == pytest.approx(3000.0 * 0.15)


def test_prejuizo_de_day_trade_nao_compensa_com_swing_e_vice_versa():
    compras = [
        # day trade com prejuízo no mês 1
        {"id": "1", "tipo": "compra", "ticker": "PETR4", "data": "2024-01-10", "qtd": 1000, "preco": 30.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "PETR4", "data": "2024-01-10", "qtd": 1000, "preco": 28.0, "taxas": 0.0},  # day trade -2000
        # swing com lucro no mês 2, mesmo ticker mas datas diferentes
        {"id": "3", "tipo": "compra", "ticker": "PETR4", "data": "2024-02-01", "qtd": 10000, "preco": 30.0, "taxas": 0.0},
        {"id": "4", "tipo": "venda", "ticker": "PETR4", "data": "2024-02-20", "qtd": 10000, "preco": 33.0, "taxas": 0.0},  # swing +30000
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    linhas = ir.resumo_mensal_ir(resultado)
    mes2 = next(l for l in linhas if l["mes"] == "2024-02")
    # o prejuízo de day trade do mês 1 NÃO pode abater o lucro de swing do mês 2
    assert mes2["swing"]["prejuizo_compensado"] == pytest.approx(0.0)
    assert mes2["swing"]["imposto"] == pytest.approx(30000.0 * 0.15)


def test_resumo_mensal_ir_swing_usa_aliquota_vigente_na_data_de_cada_mes():
    """
    Prova que resumo_mensal_ir() (a versão completa, com day trade e
    compensação de prejuízo) também consulta core.config.TABELA_IR_ACOES
    por mês para o Swing Trade — não só a versão simplificada em
    calculations.resumo_ir_mensal(). Simula uma mudança de alíquota a
    partir de 2030-01-01, removendo a linha extra no final (mesmo se o
    teste falhar no meio), sem afetar a tabela real.
    """
    from core import config as cfg

    nova_linha = {"vigente_desde": "2030-01-01", "aliquota": 0.175, "limite_isencao_mensal": 20_000.0}
    cfg.TABELA_IR_ACOES.append(nova_linha)
    try:
        resultado = ir.ResultadoIR(
            swing=[
                {"data": "2029-06-05", "qtd": 1000, "preco_venda": 30.0, "lucro": 2000.0},  # antes
                {"data": "2030-06-05", "qtd": 1000, "preco_venda": 30.0, "lucro": 2000.0},  # depois
            ],
            day_trade=[],
        )
        linhas = ir.resumo_mensal_ir(resultado)
        linha_antiga = next(l for l in linhas if l["mes"] == "2029-06")
        linha_nova = next(l for l in linhas if l["mes"] == "2030-06")
        assert linha_antiga["swing"]["imposto"] == pytest.approx(2000.0 * 0.15)
        assert linha_nova["swing"]["imposto"] == pytest.approx(2000.0 * 0.175)
    finally:
        cfg.TABELA_IR_ACOES.remove(nova_linha)


def test_day_trade_nunca_tem_isencao_mesmo_com_lucro_pequeno():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "PETR4", "data": "2024-01-10", "qtd": 100, "preco": 30.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "PETR4", "data": "2024-01-10", "qtd": 100, "preco": 31.0, "taxas": 0.0},  # lucro 100
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    linha = ir.resumo_mensal_ir(resultado)[0]
    # day trade tributa 20% sobre o lucro, sem isenção de valor mínimo vendido
    irrf_dt = 100.0 * 0.01  # 1% sobre o lucro positivo
    imposto_dt_bruto = 100.0 * 0.20
    assert linha["day_trade"]["imposto"] == pytest.approx(imposto_dt_bruto)
    assert linha["day_trade"]["irrf_estimado"] == pytest.approx(irrf_dt)


def test_regra_do_valor_minimo_10_reais_acumula_para_o_proximo_mes():
    """
    Se o DARF do mês (depois de compensar prejuízo e descontar o IRRF) ficar
    abaixo de R$10, a Receita permite não pagar naquele mês — soma para o
    próximo mês em que ultrapassar o mínimo.
    """
    compras = [
        # mês 1: vendeu acima de 20.000 (não isento) mas com margem de lucro
        # bem apertada -> DARF de ~R$2,10, abaixo do mínimo de R$10.
        {"id": "1", "tipo": "compra", "ticker": "PETR4", "data": "2024-01-01", "qtd": 2100, "preco": 10.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "PETR4", "data": "2024-01-15", "qtd": 2100, "preco": 10.01, "taxas": 0.0},
        # mês 2: lucro bem maior, que somado ao pendente do mês 1 ultrapassa 10
        {"id": "3", "tipo": "compra", "ticker": "VALE3", "data": "2024-02-01", "qtd": 10000, "preco": 50.0, "taxas": 0.0},
        {"id": "4", "tipo": "venda", "ticker": "VALE3", "data": "2024-02-15", "qtd": 10000, "preco": 51.0, "taxas": 0.0},
    ]
    resultado = ir.construir_resultados_ir(compras, [])
    linhas = ir.resumo_mensal_ir(resultado)
    mes1 = next(l for l in linhas if l["mes"] == "2024-01")
    mes2 = next(l for l in linhas if l["mes"] == "2024-02")

    assert mes1["imposto_devido_mes"] > 0
    assert mes1["darf_a_pagar"] == pytest.approx(0.0)
    assert mes1["abaixo_do_minimo"] is True

    # o DARF do mês 2 deve incluir o pendente do mês 1
    assert mes2["darf_a_pagar"] == pytest.approx(mes1["imposto_devido_mes"] + mes2["imposto_devido_mes"])


# ==========================================================================
# Posições em uma data de corte (Bens e Direitos)
# ==========================================================================

def test_posicoes_em_data_ignora_transacoes_depois_do_corte():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "ITUB4", "data": "2023-06-01", "qtd": 100, "preco": 20.0, "taxas": 0.0},
        {"id": "2", "tipo": "compra", "ticker": "ITUB4", "data": "2024-03-01", "qtd": 100, "preco": 30.0, "taxas": 0.0},
    ]
    posicoes_2023 = ir.posicoes_em_data(compras, [], "2023-12-31")
    assert len(posicoes_2023) == 1
    assert posicoes_2023[0]["qtd_total"] == pytest.approx(100.0)
    assert posicoes_2023[0]["preco_medio_ponderado"] == pytest.approx(20.0)


def test_posicoes_em_data_inclui_transacoes_exatamente_na_data_de_corte():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "ITUB4", "data": "2023-12-31", "qtd": 100, "preco": 20.0, "taxas": 0.0},
    ]
    posicoes = ir.posicoes_em_data(compras, [], "2023-12-31")
    assert len(posicoes) == 1


# ==========================================================================
# Resumo anual de proventos (Dividendos / JCP / Rendimentos de FII)
# ==========================================================================

def test_resumo_anual_proventos_separa_por_tipo_e_estima_irrf_do_jcp():
    proventos = [
        {"data": "2024-03-10", "tipo": "Dividendo", "valor": 100.0},
        {"data": "2024-04-10", "tipo": "JCP", "valor": 200.0},
        {"data": "2024-05-10", "tipo": "Rendimento", "valor": 50.0},
        {"data": "2023-01-01", "tipo": "Dividendo", "valor": 999.0},  # ano diferente, deve ser ignorado
    ]
    resumo = ir.resumo_anual_proventos(proventos, "2024")
    assert resumo["dividendos"] == pytest.approx(100.0)
    assert resumo["jcp"] == pytest.approx(200.0)
    assert resumo["rendimentos_fii"] == pytest.approx(50.0)
    assert resumo["jcp_irrf_estimado"] == pytest.approx(30.0)  # 15% de 200


def test_resumo_anual_proventos_sem_nenhum_no_ano_retorna_zeros():
    resumo = ir.resumo_anual_proventos([], "2024")
    assert resumo == {"dividendos": 0.0, "jcp": 0.0, "rendimentos_fii": 0.0, "jcp_irrf_estimado": 0.0}
