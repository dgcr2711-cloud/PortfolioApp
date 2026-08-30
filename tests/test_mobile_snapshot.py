"""
Testes automatizados de core/mobile_snapshot.py — em especial a parte
adicionada para o Piotroski F-Score, o Altman Z-Score e o "football field"
de valuation (core/piotroski.py, core/altman.py, core/valuation_multiplos.py)
chegarem até o snapshot que o celular consome, sem duplicar nenhuma fórmula
em TypeScript.

Este módulo não usa streamlit nem yfinance (só core.calculations,
core.portfolio_analytics, core.imposto_renda e ui.ativos, que também não
usam) — dá para testar de ponta a ponta no sandbox, com uma carteira de
exemplo bem pequena.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

from core import data_store, mobile_snapshot


def _carteira_de_exemplo() -> dict:
    dados = data_store.estrutura_padrao()
    dados["compras"] = [
        {"id": "1", "tipo": "compra", "ticker": "TEST3", "data": "2024-01-10", "qtd": 100, "preco": 20.0, "taxas": 0.0},
    ]
    dados["cotacoes"] = {"TEST3": {"preco": 25.0, "nome": "Teste SA", "previousClose": 24.5}}
    dados["setores"] = {"TEST3": "Tecnologia"}
    dados["precosTeto"] = {"TEST3": {"precoTeto": 30.0, "precoTetoComMargem": 24.0, "atualizadoEm": "01/01/2026"}}
    dados["fundamentos"] = {
        "TEST3": {
            "pl": 10.0, "pvp": 2.0, "lpa": 5.0, "vpa": 20.0,
            "dividend_yield": 0.05, "roe": 0.15, "margem_liquida": 0.10,
        },
    }
    dados["piotroski"] = {
        "TEST3": {
            "pontos": 7, "totalAvaliado": 9, "classificacao": "Neutra",
            "criterios": [{"chave": "roa_positivo", "rotulo": "Lucro líquido positivo", "grupo": "Rentabilidade", "passou": True}],
            "atualizadoEm": "01/01/2026 10:00",
        },
    }
    dados["altman"] = {
        "TEST3": {"zScore": 3.5, "classificacao": "Zona Segura", "atualizadoEm": "01/01/2026 10:00"},
    }
    return dados


def test_snapshot_inclui_piotroski_do_ativo():
    dados = _carteira_de_exemplo()
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    ativo = next(a for a in snapshot["ativos"] if a["ticker"] == "TEST3")
    assert ativo["piotroski"]["pontos"] == 7
    assert ativo["piotroski"]["totalAvaliado"] == 9
    assert ativo["piotroski"]["classificacao"] == "Neutra"
    assert ativo["piotroski"]["criterios"][0]["chave"] == "roa_positivo"
    assert ativo["piotroski"]["criterios"][0]["passou"] is True


def test_snapshot_inclui_altman_do_ativo():
    dados = _carteira_de_exemplo()
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    ativo = next(a for a in snapshot["ativos"] if a["ticker"] == "TEST3")
    assert ativo["altman"]["zScore"] == 3.5
    assert ativo["altman"]["classificacao"] == "Zona Segura"


def test_snapshot_sem_piotroski_ou_altman_buscados_fica_none_sem_quebrar():
    dados = _carteira_de_exemplo()
    dados["piotroski"] = {}
    dados["altman"] = {}
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    ativo = next(a for a in snapshot["ativos"] if a["ticker"] == "TEST3")
    assert ativo["piotroski"] is None
    assert ativo["altman"] is None


def test_snapshot_inclui_football_field_com_dcf_graham_e_valor_patrimonial():
    dados = _carteira_de_exemplo()
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    ativo = next(a for a in snapshot["ativos"] if a["ticker"] == "TEST3")
    ff = ativo["footballField"]
    nomes = {m["nome"] for m in ff["metodos"]}
    assert "Fluxo de Caixa Descontado" in nomes  # veio do precoTeto (30.0)
    assert "Número de Graham" in nomes  # lpa=5.0, vpa=20.0 -> ambos positivos
    assert "Valor Patrimonial por Ação" in nomes  # vpa=20.0
    # o método de múltiplo de P/L nunca aparece no celular (depende de uma
    # escolha manual feita só na sessão do PC, ver docstring do módulo)
    assert not any("Múltiplo de P/L" in n for n in nomes)
    assert ff["minimo"] is not None and ff["maximo"] is not None and ff["media"] is not None


def test_snapshot_football_field_none_quando_nenhum_metodo_da_para_calcular():
    dados = _carteira_de_exemplo()
    dados["precosTeto"] = {}  # sem FCD
    dados["fundamentos"]["TEST3"]["lpa"] = None
    dados["fundamentos"]["TEST3"]["vpa"] = None
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    ativo = next(a for a in snapshot["ativos"] if a["ticker"] == "TEST3")
    assert ativo["footballField"] is None


def test_snapshot_fundamentos_do_ativo_inclui_lpa_e_vpa():
    dados = _carteira_de_exemplo()
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    ativo = next(a for a in snapshot["ativos"] if a["ticker"] == "TEST3")
    assert ativo["fundamentos"]["lpa"] == 5.0
    assert ativo["fundamentos"]["vpa"] == 20.0


# ==========================================================================
# Risco (Beta e Sharpe, core/risco.py) — Task #27
# ==========================================================================

def test_snapshot_inclui_risco_com_aviso_quando_historico_insuficiente():
    dados = _carteira_de_exemplo()  # sem "historico" -> lista vazia
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    risco = snapshot["risco"]
    assert risco["beta"] is None
    assert risco["sharpeAnualizado"] is None
    assert risco["numeroPeriodos"] == 0
    assert risco["aviso"] is not None


def test_snapshot_inclui_risco_calculado_quando_ha_dados_suficientes():
    dados = _carteira_de_exemplo()
    dados["historico"] = [
        {"data": "2024-01-01", "totalInvestido": 10000.0, "totalAtual": 10000.0, "ibov": 100000.0},
        {"data": "2024-01-02", "totalInvestido": 10000.0, "totalAtual": 10500.0, "ibov": 103000.0},
        {"data": "2024-01-03", "totalInvestido": 10000.0, "totalAtual": 10200.0, "ibov": 101000.0},
        {"data": "2024-01-04", "totalInvestido": 10000.0, "totalAtual": 10800.0, "ibov": 104500.0},
        {"data": "2024-01-05", "totalInvestido": 10000.0, "totalAtual": 10600.0, "ibov": 103500.0},
    ]
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    risco = snapshot["risco"]
    assert risco["beta"] is not None
    assert risco["sharpeAnualizado"] is not None
    assert risco["numeroPeriodos"] == 4
    assert risco["aviso"] is None


def test_snapshot_risco_usa_taxa_livre_de_risco_configurada_em_dados():
    """Taxas diferentes -> Sharpe diferente, e o valor usado vem refletido
    de volta no snapshot (útil pro celular exibir 'calculado com X% a.a.')."""
    dados = _carteira_de_exemplo()
    dados["historico"] = [
        {"data": "2024-01-01", "totalInvestido": 10000.0, "totalAtual": 10000.0, "ibov": 100000.0},
        {"data": "2024-01-02", "totalInvestido": 10000.0, "totalAtual": 10500.0, "ibov": 103000.0},
        {"data": "2024-01-03", "totalInvestido": 10000.0, "totalAtual": 10200.0, "ibov": 101000.0},
        {"data": "2024-01-04", "totalInvestido": 10000.0, "totalAtual": 10800.0, "ibov": 104500.0},
        {"data": "2024-01-05", "totalInvestido": 10000.0, "totalAtual": 10600.0, "ibov": 103500.0},
    ]
    dados["taxaLivreRiscoAnualPct"] = 40.0
    snapshot_taxa_alta = mobile_snapshot.montar_snapshot_para_celular(dados)
    dados["taxaLivreRiscoAnualPct"] = 1.0
    snapshot_taxa_baixa = mobile_snapshot.montar_snapshot_para_celular(dados)
    assert snapshot_taxa_alta["risco"]["taxaLivreRiscoAnualPctUsada"] == 40.0
    assert snapshot_taxa_baixa["risco"]["taxaLivreRiscoAnualPctUsada"] == 1.0
    assert snapshot_taxa_alta["risco"]["sharpeAnualizado"] < snapshot_taxa_baixa["risco"]["sharpeAnualizado"]


# ==========================================================================
# Rebalanceamento (metas de alocação e desvios, core/rebalanceamento.py) — Task #28
# ==========================================================================

def test_snapshot_sem_metas_definidas_traz_lista_vazia():
    dados = _carteira_de_exemplo()  # sem "metasAlocacao" -> {}
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    rebalanceamento = snapshot["rebalanceamento"]
    assert rebalanceamento["temMetas"] is False
    assert rebalanceamento["desvios"] == []


def test_snapshot_com_metas_definidas_traz_desvio_do_ativo():
    dados = _carteira_de_exemplo()  # só TEST3, 100 ações a 25.0 -> atual = 2500.0 -> 100% da carteira
    dados["metasAlocacao"] = {"TEST3": 50.0}
    snapshot = mobile_snapshot.montar_snapshot_para_celular(dados)
    rebalanceamento = snapshot["rebalanceamento"]
    assert rebalanceamento["temMetas"] is True
    desvio = rebalanceamento["desvios"][0]
    assert desvio["ticker"] == "TEST3"
    assert desvio["metaPct"] == 50.0
    assert desvio["atualPct"] == 100.0
    assert desvio["desvioPp"] == 50.0
    assert desvio["alerta"] is True
    assert desvio["valorAjuste"] < 0  # está acima da meta -> venderia
