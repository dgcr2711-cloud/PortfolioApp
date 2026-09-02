"""
Testes automatizados de core/calculations.py — o motor de cálculo (preço
médio, preço teto/FCD, resultado realizado, IR simplificado, proventos,
TWR vs. Ibovespa).

Como rodar (depois de instalar as dependências de teste uma vez):

    pip install -r requirements-dev.txt
    pytest -v

ou simplesmente dê um duplo-clique em "Rodar Testes.bat".

Cada teste aqui é uma "prova": monta uma carteira de exemplo bem simples,
com números fáceis de conferir na mão/calculadora, e verifica que a função
devolve exatamente o que deveria. Se algum dia uma alteração no código
quebrar sem querer uma dessas contas, o teste correspondente fica vermelho
na hora — antes que o erro chegue até a tela do app.
"""

from __future__ import annotations

import pytest

from core import calculations as calc


# ==========================================================================
# construir_ledger / consolidar_posicoes
# ==========================================================================

def test_ledger_compra_simples_calcula_preco_medio():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "PETR4", "data": "2024-01-10", "qtd": 100, "preco": 30.0, "taxas": 10.0},
    ]
    ledger = calc.construir_ledger(compras, [])
    pos = ledger.posicoes["PETR4"]
    assert pos["qtd"] == 100
    # custo = 100*30 + 10 = 3010 -> preço médio = 30.10
    assert pos["custo_total"] == pytest.approx(3010.0)


def test_ledger_duas_compras_pondera_preco_medio():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "VALE3", "data": "2024-01-10", "qtd": 100, "preco": 60.0, "taxas": 0.0},
        {"id": "2", "tipo": "compra", "ticker": "VALE3", "data": "2024-02-10", "qtd": 100, "preco": 70.0, "taxas": 0.0},
    ]
    posicoes = calc.consolidar_posicoes(compras, [])
    assert len(posicoes) == 1
    # preço médio ponderado = (100*60 + 100*70) / 200 = 65
    assert posicoes[0]["preco_medio_ponderado"] == pytest.approx(65.0)
    assert posicoes[0]["qtd_total"] == 200


def test_ledger_venda_usa_preco_medio_na_data_nao_preco_de_compra_especifico():
    """
    Regra do dashboard original: ao vender, o custo baixado é o PREÇO MÉDIO
    da posição naquele momento — não importa qual "lote" de compra específico
    está "saindo". Compra 100 a 10, compra 100 a 20 (médio 15), vende 50 a 25:
    lucro = 50*25 - 50*15 = 1250 - 750 = 500.
    """
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "ITUB4", "data": "2024-01-01", "qtd": 100, "preco": 10.0, "taxas": 0.0},
        {"id": "2", "tipo": "compra", "ticker": "ITUB4", "data": "2024-01-02", "qtd": 100, "preco": 20.0, "taxas": 0.0},
        {"id": "3", "tipo": "venda", "ticker": "ITUB4", "data": "2024-01-03", "qtd": 50, "preco": 25.0, "taxas": 0.0},
    ]
    ledger = calc.construir_ledger(compras, [])
    assert len(ledger.resultados_realizados) == 1
    resultado = ledger.resultados_realizados[0]
    assert resultado["custo_base"] == pytest.approx(15.0 * 50)
    assert resultado["lucro"] == pytest.approx(500.0)
    # posição restante: 150 ações, custo total = 3000 - 750 = 2250 -> médio 15
    pos = ledger.posicoes["ITUB4"]
    assert pos["qtd"] == pytest.approx(150.0)
    assert pos["custo_total"] == pytest.approx(2250.0)


def test_ledger_venda_maior_que_posicao_gera_aviso_e_nao_fica_negativa():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "MGLU3", "data": "2024-01-01", "qtd": 100, "preco": 5.0, "taxas": 0.0},
        {"id": "2", "tipo": "venda", "ticker": "MGLU3", "data": "2024-01-02", "qtd": 500, "preco": 6.0, "taxas": 0.0},
    ]
    ledger = calc.construir_ledger(compras, [])
    assert len(ledger.avisos) == 1
    assert "MGLU3" in ledger.avisos[0]
    # a posição nunca fica negativa: vendeu no máximo o que tinha (100)
    assert ledger.posicoes["MGLU3"]["qtd"] == pytest.approx(0.0)


def test_ledger_evento_desdobramento_multiplica_qtd_mas_nao_o_custo():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "KLBN4", "data": "2024-01-01", "qtd": 100, "preco": 20.0, "taxas": 0.0},
    ]
    eventos = [
        {"id": "e1", "ticker": "KLBN4", "data": "2024-02-01", "fator": 4},  # desdobramento 1:4
    ]
    ledger = calc.construir_ledger(compras, eventos)
    pos = ledger.posicoes["KLBN4"]
    assert pos["qtd"] == pytest.approx(400.0)
    assert pos["custo_total"] == pytest.approx(2000.0)  # custo não muda
    posicoes = calc.consolidar_posicoes(compras, eventos)
    # preço médio se ajusta sozinho: 2000/400 = 5
    assert posicoes[0]["preco_medio_ponderado"] == pytest.approx(5.0)


def test_calcular_posicoes_completas_usa_cotacao_e_calcula_variacao_do_dia():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "WEGE3", "data": "2024-01-01", "qtd": 10, "preco": 40.0, "taxas": 0.0},
    ]
    cotacoes = {"WEGE3": {"preco": 50.0, "previousClose": 45.0}}
    completas = calc.calcular_posicoes_completas(compras, [], cotacoes)
    assert len(completas) == 1
    p = completas[0]
    assert p["atual"] == pytest.approx(500.0)
    assert p["lucro_reais"] == pytest.approx(100.0)  # 500 - 400
    assert p["lucro_pct"] == pytest.approx(25.0)
    # variação do dia: (50-45)/45*100, e em reais: (50-45)*10
    assert p["variacao_dia_pct"] == pytest.approx((5 / 45) * 100)
    assert p["variacao_dia_reais"] == pytest.approx(50.0)


def test_calcular_posicoes_completas_sem_cotacao_usa_preco_medio():
    compras = [
        {"id": "1", "tipo": "compra", "ticker": "BBAS3", "data": "2024-01-01", "qtd": 10, "preco": 30.0, "taxas": 0.0},
    ]
    completas = calc.calcular_posicoes_completas(compras, [], cotacoes={})
    assert completas[0]["cotacao_atual"] == pytest.approx(30.0)
    assert completas[0]["variacao_dia_pct"] is None


def test_totais_carteira_soma_posicoes():
    posicoes_completas = [
        {"valor_total_investido": 1000.0, "atual": 1200.0, "variacao_dia_reais": 20.0},
        {"valor_total_investido": 500.0, "atual": 400.0, "variacao_dia_reais": -5.0},
    ]
    totais = calc.totais_carteira(posicoes_completas)
    assert totais["total_investido"] == pytest.approx(1500.0)
    assert totais["total_atual"] == pytest.approx(1600.0)
    assert totais["lucro"] == pytest.approx(100.0)
    assert totais["rentabilidade_pct"] == pytest.approx(100.0 / 1500.0 * 100)
    assert totais["variacao_dia_reais"] == pytest.approx(15.0)


# ==========================================================================
# Preço Teto / margem de segurança / indicação
# ==========================================================================

def test_preco_com_margem_padrao_20_por_cento():
    assert calc.preco_com_margem(100.0) == pytest.approx(80.0)


def test_preco_com_margem_customizada():
    assert calc.preco_com_margem(100.0, margem=0.30) == pytest.approx(70.0)


@pytest.mark.parametrize(
    "cotacao,esperado",
    [
        (75.0, "compra"),   # abaixo da margem (80)
        (80.0, "compra"),   # exatamente na margem
        (90.0, "neutro"),   # entre margem (80) e teto (100)
        (100.0, "neutro"),  # exatamente no teto
        (110.0, "venda"),   # acima do teto
    ],
)
def test_indicacao_compra_neutro_venda(cotacao, esperado):
    assert calc.indicacao(preco_teto=100.0, cotacao_atual=cotacao) == esperado


def test_indicacao_none_quando_falta_preco_teto_ou_cotacao():
    assert calc.indicacao(preco_teto=None, cotacao_atual=50.0) is None
    assert calc.indicacao(preco_teto=100.0, cotacao_atual=None) is None


def test_margem_vs_preco_medio():
    # preço teto 100, preço médio pago 80 -> margem de 20%
    assert calc.margem_vs_preco_medio(100.0, 80.0) == pytest.approx(20.0)
    assert calc.margem_vs_preco_medio(None, 80.0) is None


# ==========================================================================
# resumo_ir_mensal (estimativa simplificada)
# ==========================================================================

def test_resumo_ir_mensal_isento_ate_20_mil_no_mes():
    resultados = [
        {"data": "2024-03-05", "qtd": 100, "preco_venda": 100.0, "lucro": 500.0},  # vendeu 10.000
    ]
    linhas = calc.resumo_ir_mensal(resultados)
    assert len(linhas) == 1
    assert linhas[0]["isento"] is True
    assert linhas[0]["imposto_estimado"] == pytest.approx(0.0)


def test_resumo_ir_mensal_tributa_15_por_cento_acima_de_20_mil():
    resultados = [
        {"data": "2024-03-05", "qtd": 1000, "preco_venda": 30.0, "lucro": 2000.0},  # vendeu 30.000
    ]
    linhas = calc.resumo_ir_mensal(resultados)
    assert linhas[0]["isento"] is False
    assert linhas[0]["imposto_estimado"] == pytest.approx(2000.0 * 0.15)


def test_resumo_ir_mensal_agrupa_por_mes_mais_recente_primeiro():
    resultados = [
        {"data": "2024-01-10", "qtd": 10, "preco_venda": 10.0, "lucro": 10.0},
        {"data": "2024-03-10", "qtd": 10, "preco_venda": 10.0, "lucro": 20.0},
    ]
    linhas = calc.resumo_ir_mensal(resultados)
    assert [l["mes"] for l in linhas] == ["2024-03", "2024-01"]


def test_resumo_ir_mensal_usa_aliquota_vigente_na_data_de_cada_mes():
    """
    Prova que resumo_ir_mensal() de fato consulta core.config.TABELA_IR_ACOES
    por mês (via regra_ir_vigente_em), em vez de usar uma alíquota fixa —
    simula uma mudança de alíquota a partir de 2030-01-01 (sem alterar a
    tabela real de verdade: a linha extra é removida no final do teste,
    mesmo se o teste falhar no meio).
    """
    from core import config as cfg

    nova_linha = {"vigente_desde": "2030-01-01", "aliquota": 0.175, "limite_isencao_mensal": 20_000.0}
    cfg.TABELA_IR_ACOES.append(nova_linha)
    try:
        resultados = [
            {"data": "2029-06-05", "qtd": 1000, "preco_venda": 30.0, "lucro": 2000.0},  # antes da mudança
            {"data": "2030-06-05", "qtd": 1000, "preco_venda": 30.0, "lucro": 2000.0},  # depois da mudança
        ]
        linhas = calc.resumo_ir_mensal(resultados)
        linha_antiga = next(l for l in linhas if l["mes"] == "2029-06")
        linha_nova = next(l for l in linhas if l["mes"] == "2030-06")
        assert linha_antiga["imposto_estimado"] == pytest.approx(2000.0 * 0.15)
        assert linha_nova["imposto_estimado"] == pytest.approx(2000.0 * 0.175)
    finally:
        cfg.TABELA_IR_ACOES.remove(nova_linha)


def test_resumo_ir_mensal_usa_limite_de_isencao_vigente_na_data_de_cada_mes():
    from core import config as cfg

    nova_linha = {"vigente_desde": "2030-01-01", "aliquota": 0.15, "limite_isencao_mensal": 25_000.0}
    cfg.TABELA_IR_ACOES.append(nova_linha)
    try:
        # mesma venda (22.000 no mês) nos dois lados da mudança: acima do
        # limite antigo (20 mil) mas dentro do limite novo (25 mil)
        resultados = [
            {"data": "2029-06-05", "qtd": 220, "preco_venda": 100.0, "lucro": 1000.0},
            {"data": "2030-06-05", "qtd": 220, "preco_venda": 100.0, "lucro": 1000.0},
        ]
        linhas = calc.resumo_ir_mensal(resultados)
        linha_antiga = next(l for l in linhas if l["mes"] == "2029-06")
        linha_nova = next(l for l in linhas if l["mes"] == "2030-06")
        assert linha_antiga["isento"] is False
        assert linha_antiga["imposto_estimado"] == pytest.approx(150.0)
        assert linha_nova["isento"] is True
        assert linha_nova["imposto_estimado"] == pytest.approx(0.0)
    finally:
        cfg.TABELA_IR_ACOES.remove(nova_linha)


# ==========================================================================
# Proventos
# ==========================================================================

def test_resumo_proventos_total_geral_e_yield_on_cost():
    hoje_menos_10_dias = "2020-01-01"  # bem antigo, não entra no 12m
    proventos = [
        {"valor": 100.0, "data": hoje_menos_10_dias},
        {"valor": 50.0, "data": "2999-01-01"},  # data futura: garante que entra no 12m em qualquer época em que o teste rode
    ]
    resumo = calc.resumo_proventos(proventos, total_investido_atual=1000.0)
    assert resumo["total_geral"] == pytest.approx(150.0)
    assert resumo["total_12m"] == pytest.approx(50.0)
    assert resumo["yield_on_cost"] == pytest.approx(5.0)


def test_resumo_proventos_total_investido_zero_nao_quebra():
    resumo = calc.resumo_proventos([], total_investido_atual=0.0)
    assert resumo["yield_on_cost"] == 0.0


def test_resumo_proventos_por_tipo_agrupa_e_soma_por_tipo():
    proventos = [
        {"valor": 100.0, "tipo": "Dividendo"},
        {"valor": 30.0, "tipo": "JCP"},
        {"valor": 20.0, "tipo": "Dividendo"},
        {"valor": 15.0, "tipo": "Rendimento"},
    ]
    linhas = calc.resumo_proventos_por_tipo(proventos)

    por_tipo = {l["tipo"]: l for l in linhas}
    assert por_tipo["Dividendo"]["total"] == pytest.approx(120.0)
    assert por_tipo["Dividendo"]["quantidade"] == 2
    assert por_tipo["JCP"]["total"] == pytest.approx(30.0)
    assert por_tipo["JCP"]["quantidade"] == 1
    assert por_tipo["Rendimento"]["total"] == pytest.approx(15.0)


def test_resumo_proventos_por_tipo_ordena_do_maior_pro_menor():
    proventos = [
        {"valor": 10.0, "tipo": "Rendimento"},
        {"valor": 500.0, "tipo": "Dividendo"},
        {"valor": 200.0, "tipo": "JCP"},
    ]
    linhas = calc.resumo_proventos_por_tipo(proventos)
    assert [l["tipo"] for l in linhas] == ["Dividendo", "JCP", "Rendimento"]


def test_resumo_proventos_por_tipo_lista_vazia_sem_proventos():
    assert calc.resumo_proventos_por_tipo([]) == []


def test_mapa_dividendos_por_ticker_agrupa_meses_e_calcula_valor_medio():
    proventos = [
        {"ticker": "ITUB4", "data": "2025-03-10", "valor": 10.0},
        {"ticker": "ITUB4", "data": "2025-06-10", "valor": 20.0},
        {"ticker": "ITUB4", "data": "2024-03-15", "valor": 30.0},  # mesmo mês (março) de novo, ano diferente
        {"ticker": "VALE3", "data": "2025-01-05", "valor": 100.0},
    ]
    mapa = calc.mapa_dividendos_por_ticker(proventos)
    por_ticker = {m["ticker"]: m for m in mapa}

    assert por_ticker["ITUB4"]["meses"] == [3, 6]  # março aparece 1x na lista de meses, não repetido
    assert por_ticker["ITUB4"]["quantidade_pagamentos"] == 3
    assert por_ticker["ITUB4"]["valor_medio_por_pagamento"] == pytest.approx(20.0)  # (10+20+30)/3
    assert por_ticker["ITUB4"]["contagem_por_mes"] == {3: 2, 6: 1}  # março pagou 2x (anos diferentes), junho 1x

    assert por_ticker["VALE3"]["meses"] == [1]
    assert por_ticker["VALE3"]["valor_medio_por_pagamento"] == pytest.approx(100.0)
    assert por_ticker["VALE3"]["contagem_por_mes"] == {1: 1}


def test_mapa_dividendos_por_ticker_ordena_por_ticker():
    proventos = [
        {"ticker": "VALE3", "data": "2025-01-05", "valor": 1.0},
        {"ticker": "ITUB4", "data": "2025-01-05", "valor": 1.0},
        {"ticker": "PETR4", "data": "2025-01-05", "valor": 1.0},
    ]
    mapa = calc.mapa_dividendos_por_ticker(proventos)
    assert [m["ticker"] for m in mapa] == ["ITUB4", "PETR4", "VALE3"]


def test_mapa_dividendos_por_ticker_ignora_provento_sem_data_valida():
    proventos = [
        {"ticker": "ITUB4", "data": "2025-03-10", "valor": 10.0},
        {"ticker": "ITUB4", "data": "", "valor": 999.0},
        {"ticker": "ITUB4", "data": None, "valor": 999.0},
    ]
    mapa = calc.mapa_dividendos_por_ticker(proventos)
    assert mapa[0]["quantidade_pagamentos"] == 1
    assert mapa[0]["valor_medio_por_pagamento"] == pytest.approx(10.0)


def test_mapa_dividendos_por_ticker_lista_vazia_sem_proventos():
    assert calc.mapa_dividendos_por_ticker([]) == []


def test_mapa_dividendos_por_ticker_data_minima_ignora_proventos_anteriores():
    proventos = [
        {"ticker": "ITUB4", "data": "2026-02-15", "valor": 999.0},  # antes do corte
        {"ticker": "ITUB4", "data": "2026-03-01", "valor": 10.0},   # exatamente no corte
        {"ticker": "ITUB4", "data": "2026-06-10", "valor": 20.0},
    ]
    mapa = calc.mapa_dividendos_por_ticker(proventos, data_minima="2026-03-01")
    por_ticker = {m["ticker"]: m for m in mapa}
    assert por_ticker["ITUB4"]["quantidade_pagamentos"] == 2  # o de fevereiro ficou de fora
    assert por_ticker["ITUB4"]["valor_medio_por_pagamento"] == pytest.approx(15.0)  # (10+20)/2


def test_mapa_dividendos_por_ticker_data_minima_none_nao_filtra_nada():
    proventos = [{"ticker": "ITUB4", "data": "2020-01-01", "valor": 10.0}]
    mapa = calc.mapa_dividendos_por_ticker(proventos, data_minima=None)
    assert mapa[0]["quantidade_pagamentos"] == 1


def test_fluxo_mensal_estimado_dividendos_soma_por_mes_entre_tickers():
    proventos = [
        {"ticker": "ITUB4", "data": "2025-03-10", "valor": 10.0},   # ITUB4 paga em março
        {"ticker": "VALE3", "data": "2025-03-20", "valor": 50.0},   # VALE3 também paga em março
        {"ticker": "VALE3", "data": "2025-09-20", "valor": 50.0},   # e em setembro
    ]
    fluxo = calc.fluxo_mensal_estimado_dividendos(proventos)

    assert len(fluxo) == 12
    assert fluxo[2] == pytest.approx(60.0)  # março (índice 2): 10 (ITUB4) + 50 (VALE3)
    assert fluxo[8] == pytest.approx(50.0)  # setembro (índice 8): só VALE3
    assert fluxo[0] == pytest.approx(0.0)   # janeiro: nada


def test_fluxo_mensal_estimado_dividendos_lista_de_zeros_sem_proventos():
    assert calc.fluxo_mensal_estimado_dividendos([]) == [0.0] * 12


def test_fluxo_mensal_estimado_dividendos_respeita_data_minima():
    proventos = [
        {"ticker": "ITUB4", "data": "2025-03-10", "valor": 10.0},  # antes do corte, deve sumir
        {"ticker": "VALE3", "data": "2026-09-20", "valor": 50.0},
    ]
    fluxo = calc.fluxo_mensal_estimado_dividendos(proventos, data_minima="2026-03-01")
    assert fluxo[2] == pytest.approx(0.0)   # março: o provento de ITUB4 foi filtrado
    assert fluxo[8] == pytest.approx(50.0)  # setembro: VALE3 continua


# ==========================================================================
# enriquecer_proximos_com_total
# ==========================================================================

def _compra(ticker, data, qtd, preco=10.0, tipo="compra"):
    return {"ticker": ticker, "data": data, "qtd": qtd, "preco": preco, "taxas": 0.0, "tipo": tipo}


def test_enriquecer_proximos_com_total_data_com_futura_usa_quantidade_de_hoje():
    proximos = [{"ticker": "ITUB4", "valor_por_acao": 0.015, "tipo": "JCP", "data_com": "2026-12-01"}]
    compras = [_compra("ITUB4", "2026-03-10", 200)]
    resultado = calc.enriquecer_proximos_com_total(proximos, compras, [], hoje="2026-08-31")
    assert resultado[0]["quantidade"] == pytest.approx(200.0)
    assert resultado[0]["total"] == pytest.approx(3.0)  # 0.015 * 200
    assert resultado[0]["sem_direito"] is False


def test_enriquecer_proximos_com_total_zero_para_ticker_so_watchlist():
    proximos = [{"ticker": "PETR4", "valor_por_acao": 0.47, "tipo": "Dividendo", "data_com": "2026-12-01"}]
    resultado = calc.enriquecer_proximos_com_total(proximos, compras=[], eventos=[], hoje="2026-08-31")
    assert resultado[0]["quantidade"] == 0.0
    assert resultado[0]["total"] == 0.0
    assert resultado[0]["quantidade_hoje"] == 0.0
    assert resultado[0]["sem_direito"] is False  # não tem o ativo hoje, não é "comprou depois"


def test_enriquecer_proximos_com_total_comprou_depois_da_data_com_fica_sem_direito():
    # Exatamente o caso relatado: comprou CPFE3 DEPOIS da Data Com de um
    # provento já anunciado — tem o ativo hoje, mas não tinha na Data Com.
    proximos = [{"ticker": "CPFE3", "valor_por_acao": 3.73, "tipo": "Dividendo", "data_com": "2026-04-29"}]
    compras = [_compra("CPFE3", "2026-05-15", 100)]  # comprou DEPOIS da Data Com
    resultado = calc.enriquecer_proximos_com_total(proximos, compras, [], hoje="2026-08-31")
    assert resultado[0]["quantidade"] == 0.0       # não valia pra esse provento
    assert resultado[0]["total"] == 0.0
    assert resultado[0]["quantidade_hoje"] == pytest.approx(100.0)  # mas tem o ativo hoje
    assert resultado[0]["sem_direito"] is True


def test_enriquecer_proximos_com_total_comprou_antes_da_data_com_tem_direito():
    proximos = [{"ticker": "CPFE3", "valor_por_acao": 3.73, "tipo": "Dividendo", "data_com": "2026-04-29"}]
    compras = [_compra("CPFE3", "2026-03-01", 100)]  # comprou ANTES da Data Com
    resultado = calc.enriquecer_proximos_com_total(proximos, compras, [], hoje="2026-08-31")
    assert resultado[0]["quantidade"] == pytest.approx(100.0)
    assert resultado[0]["total"] == pytest.approx(373.0)
    assert resultado[0]["sem_direito"] is False


def test_enriquecer_proximos_com_total_venda_antes_da_data_com_tambem_fica_sem_direito():
    proximos = [{"ticker": "CPFE3", "valor_por_acao": 3.73, "tipo": "Dividendo", "data_com": "2026-04-29"}]
    compras = [
        _compra("CPFE3", "2026-01-01", 100),
        _compra("CPFE3", "2026-04-01", 100, tipo="venda"),  # vendeu tudo antes da Data Com
    ]
    resultado = calc.enriquecer_proximos_com_total(proximos, compras, [], hoje="2026-08-31")
    assert resultado[0]["quantidade"] == 0.0
    assert resultado[0]["quantidade_hoje"] == 0.0  # também não tem mais hoje
    assert resultado[0]["sem_direito"] is False  # não é "comprou depois": nunca teve na Data Com nem tem hoje


def test_enriquecer_proximos_com_total_data_com_ausente_usa_quantidade_de_hoje():
    proximos = [{"ticker": "ITUB4", "valor_por_acao": 0.015, "tipo": "JCP", "data_com": None}]
    compras = [_compra("ITUB4", "2026-03-10", 200)]
    resultado = calc.enriquecer_proximos_com_total(proximos, compras, [], hoje="2026-08-31")
    assert resultado[0]["quantidade"] == pytest.approx(200.0)


def test_enriquecer_proximos_com_total_nao_modifica_o_item_original():
    original = {"ticker": "ITUB4", "valor_por_acao": 0.015, "tipo": "JCP", "data_com": "2026-12-01"}
    proximos = [original]
    calc.enriquecer_proximos_com_total(proximos, [_compra("ITUB4", "2026-03-10", 100)], [], hoje="2026-08-31")
    assert "total" not in original  # o dict original não foi alterado, só uma cópia


def test_enriquecer_proximos_com_total_preserva_ordem():
    proximos = [
        {"ticker": "VALE3", "valor_por_acao": 1.0, "tipo": "Dividendo", "data_com": "2026-12-01"},
        {"ticker": "ITUB4", "valor_por_acao": 2.0, "tipo": "JCP", "data_com": "2026-12-01"},
    ]
    resultado = calc.enriquecer_proximos_com_total(proximos, [], [], hoje="2026-08-31")
    assert [r["ticker"] for r in resultado] == ["VALE3", "ITUB4"]


def test_enriquecer_proximos_com_total_lista_vazia():
    assert calc.enriquecer_proximos_com_total([], [], [], hoje="2026-08-31") == []


# ==========================================================================
# TWR vs. Ibovespa
# ==========================================================================

def test_twr_vs_ibovespa_none_com_menos_de_2_snapshots_com_ibov():
    assert calc.twr_vs_ibovespa([{"data": "2024-01-01", "ibov": 100000, "totalAtual": 1000, "totalInvestido": 1000}]) is None
    assert calc.twr_vs_ibovespa([]) is None


def test_twr_vs_ibovespa_sem_aporte_bate_com_retorno_simples():
    historico = [
        {"data": "2024-01-01", "ibov": 100000, "totalAtual": 1000.0, "totalInvestido": 1000.0},
        {"data": "2024-02-01", "ibov": 110000, "totalAtual": 1100.0, "totalInvestido": 1000.0},
    ]
    resultado = calc.twr_vs_ibovespa(historico)
    assert resultado is not None
    assert resultado["rent_carteira_pct"] == pytest.approx(10.0)
    assert resultado["rent_ibov_pct"] == pytest.approx(10.0)


def test_twr_vs_ibovespa_desconta_aporte_do_calculo_de_rentabilidade():
    """
    Se o total investido subiu (novo aporte) na mesma proporção que o total
    atual, isso NÃO deveria contar como "ganho de mercado" — a rentabilidade
    real da carteira nesse sub-período deve ser ~0%, mesmo o patrimônio tendo
    dobrado.
    """
    historico = [
        {"data": "2024-01-01", "ibov": 100000, "totalAtual": 1000.0, "totalInvestido": 1000.0},
        {"data": "2024-02-01", "ibov": 100000, "totalAtual": 2000.0, "totalInvestido": 2000.0},  # aporte de 1000
    ]
    resultado = calc.twr_vs_ibovespa(historico)
    assert resultado["rent_carteira_pct"] == pytest.approx(0.0)


# ==========================================================================
# Fluxo de Caixa Descontado (Preço Teto avançado)
# ==========================================================================

def test_calcular_fcd_projeta_e_desconta_fluxos():
    resultado = calc.calcular_fcd(
        fcf_base=1000.0, g1_pct=10.0, anos=5, wacc_pct=12.0,
        g2_pct=3.0, divida_liquida=0.0, n_acoes=100.0, margem_pct=20.0,
    )
    assert resultado.preco_teto > 0
    assert len(resultado.projecao) == 5
    # com margem de 20%, o preço com margem deve ser 80% do preço teto
    assert resultado.preco_teto_com_margem == pytest.approx(resultado.preco_teto * 0.8)
    # valor da empresa = soma dos VPs dos fluxos + VP terminal
    assert resultado.valor_empresa == pytest.approx(resultado.vp_fluxos + resultado.vp_terminal)


def test_calcular_fcd_desconta_divida_liquida_do_equity():
    sem_divida = calc.calcular_fcd(1000.0, 10.0, 5, 12.0, 3.0, divida_liquida=0.0, n_acoes=100.0, margem_pct=0.0)
    com_divida = calc.calcular_fcd(1000.0, 10.0, 5, 12.0, 3.0, divida_liquida=5000.0, n_acoes=100.0, margem_pct=0.0)
    assert com_divida.valor_equity == pytest.approx(sem_divida.valor_equity - 5000.0)
    assert com_divida.preco_teto == pytest.approx(sem_divida.preco_teto - 50.0)  # 5000/100 ações


def test_calcular_fcd_wacc_menor_ou_igual_a_g2_lanca_erro():
    with pytest.raises(ValueError):
        calc.calcular_fcd(1000.0, 10.0, 5, wacc_pct=3.0, g2_pct=3.0, divida_liquida=0.0, n_acoes=100.0, margem_pct=0.0)
    with pytest.raises(ValueError):
        calc.calcular_fcd(1000.0, 10.0, 5, wacc_pct=2.0, g2_pct=3.0, divida_liquida=0.0, n_acoes=100.0, margem_pct=0.0)
