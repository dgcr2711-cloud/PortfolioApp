"""
Testes automatizados de core/piotroski.py — o cálculo puro do Piotroski
F-Score (9 critérios binários a partir de dois anos fiscais). Como o
módulo não fala com o Yahoo Finance, todos os testes usam números
inventados, fáceis de conferir na mão.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import pytest

from core import piotroski


def _dados_empresa_saudavel() -> dict:
    """Uma empresa fictícia que melhorou em TODOS os 9 critérios ano a ano —
    deve fechar com pontuação máxima (9/9)."""
    return {
        "lucro_liquido_atual": 1_000_000.0,
        "lucro_liquido_anterior": 800_000.0,
        "ativos_totais_atual": 10_000_000.0,
        "ativos_totais_anterior": 9_500_000.0,
        "fluxo_caixa_operacional_atual": 1_500_000.0,  # > lucro líquido -> qualidade do lucro OK
        "divida_longo_prazo_atual": 1_000_000.0,        # 10% dos ativos
        "divida_longo_prazo_anterior": 1_425_000.0,     # 15% dos ativos -> alavancagem caiu
        "ativo_circulante_atual": 3_000_000.0,
        "passivo_circulante_atual": 1_000_000.0,        # liquidez 3.0
        "ativo_circulante_anterior": 2_000_000.0,
        "passivo_circulante_anterior": 1_000_000.0,     # liquidez 2.0 -> melhorou
        "num_acoes_atual": 1_000_000.0,
        "num_acoes_anterior": 1_000_000.0,               # igual -> sem diluição (critério tolera empate)
        "margem_bruta_atual": 0.45,
        "margem_bruta_anterior": 0.40,
        "receita_atual": 5_000_000.0,                    # giro 0.5
        "receita_anterior": 4_000_000.0,                 # giro anterior ~0.421 -> melhorou
    }


def _dados_empresa_fraca() -> dict:
    """O espelho da anterior: piorou em todos os 9 critérios -> 0/9."""
    return {
        "lucro_liquido_atual": -100_000.0,   # prejuízo -> critério 1 falha
        "lucro_liquido_anterior": 800_000.0,
        "ativos_totais_atual": 10_000_000.0,
        "ativos_totais_anterior": 9_500_000.0,
        "fluxo_caixa_operacional_atual": -200_000.0,  # negativo E mais negativo que o lucro -> critérios 2 e 4 falham
        "divida_longo_prazo_atual": 2_000_000.0,      # 20% dos ativos
        "divida_longo_prazo_anterior": 950_000.0,     # 10% -> alavancagem SUBIU -> falha
        "ativo_circulante_atual": 1_000_000.0,
        "passivo_circulante_atual": 1_000_000.0,      # liquidez 1.0
        "ativo_circulante_anterior": 2_000_000.0,
        "passivo_circulante_anterior": 1_000_000.0,   # liquidez anterior 2.0 -> piorou
        "num_acoes_atual": 1_200_000.0,
        "num_acoes_anterior": 1_000_000.0,             # emitiu mais ações -> diluiu -> falha
        "margem_bruta_atual": 0.30,
        "margem_bruta_anterior": 0.40,                 # piorou
        "receita_atual": 3_000_000.0,
        "receita_anterior": 4_000_000.0,               # giro caiu -> falha
    }


def test_empresa_saudavel_fecha_com_pontuacao_maxima():
    resultado = piotroski.calcular_piotroski(_dados_empresa_saudavel())
    assert resultado.pontos == 9
    assert resultado.total_avaliado == 9
    assert resultado.completo is True
    assert resultado.classificacao == "Forte"
    # confere que TODOS os 9 critérios individualmente passaram
    assert all(c.passou is True for c in resultado.criterios)


def test_empresa_fraca_fecha_com_pontuacao_minima():
    resultado = piotroski.calcular_piotroski(_dados_empresa_fraca())
    assert resultado.pontos == 0
    assert resultado.total_avaliado == 9
    assert resultado.classificacao == "Fraca"
    assert all(c.passou is False for c in resultado.criterios)


def test_dicionario_vazio_nao_avalia_nenhum_criterio_e_nao_lanca_erro():
    resultado = piotroski.calcular_piotroski({})
    assert resultado.pontos == 0
    assert resultado.total_avaliado == 0
    assert resultado.completo is False
    assert resultado.classificacao == "Dados parciais (0/9 critérios avaliados)"
    assert all(c.passou is None for c in resultado.criterios)


def test_dados_parciais_nao_contam_ponto_a_favor_nem_contra():
    dados = _dados_empresa_saudavel()
    del dados["fluxo_caixa_operacional_atual"]  # derruba os critérios 2 e 4, que dependem disso
    resultado = piotroski.calcular_piotroski(dados)
    assert resultado.total_avaliado == 7  # 9 - 2 (cfo_positivo, qualidade_do_lucro)
    assert resultado.pontos == 7  # os outros 7 continuam passando
    assert resultado.completo is False
    assert resultado.classificacao.startswith("Dados parciais")
    criterio_cfo = next(c for c in resultado.criterios if c.chave == "cfo_positivo")
    criterio_qualidade = next(c for c in resultado.criterios if c.chave == "qualidade_do_lucro")
    assert criterio_cfo.passou is None
    assert criterio_qualidade.passou is None


def test_classificacao_neutra_no_meio_da_faixa():
    dados = _dados_empresa_saudavel()
    # derruba 4 dos 9 critérios pra pontuação (5) cair na faixa "Neutra" —
    # mas isso também tornaria o resultado incompleto, então em vez disso
    # fazemos 4 critérios FALHAREM (não ficarem None) mudando os números.
    dados["fluxo_caixa_operacional_atual"] = dados["lucro_liquido_atual"] - 1  # qualidade do lucro falha (cfo < lucro), mas continua positivo (critério 2 continua ok)
    dados["divida_longo_prazo_atual"], dados["divida_longo_prazo_anterior"] = (
        dados["divida_longo_prazo_anterior"], dados["divida_longo_prazo_atual"],
    )  # inverte -> alavancagem parece ter subido -> falha
    dados["margem_bruta_atual"], dados["margem_bruta_anterior"] = dados["margem_bruta_anterior"], dados["margem_bruta_atual"]  # falha
    dados["num_acoes_atual"] = dados["num_acoes_anterior"] + 1  # diluiu -> falha
    resultado = piotroski.calcular_piotroski(dados)
    assert resultado.total_avaliado == 9
    assert resultado.pontos == 5  # 9 - 4 críterios derrubados de propósito
    assert resultado.classificacao == "Neutra"


def test_criterio_de_alavancagem_exige_queda_estrita_empate_nao_conta():
    # Dicionário isolado (só os 4 campos que esse critério usa): dívida e
    # ativos idênticos nos dois anos -> a razão dívida/ativos fica EXATAMENTE
    # igual (0.10 nos dois) -> não caiu -> não deve pontuar.
    dados = {
        "divida_longo_prazo_atual": 1_000_000.0,
        "divida_longo_prazo_anterior": 1_000_000.0,
        "ativos_totais_atual": 10_000_000.0,
        "ativos_totais_anterior": 10_000_000.0,
    }
    resultado = piotroski.calcular_piotroski(dados)
    criterio = next(c for c in resultado.criterios if c.chave == "alavancagem_caiu")
    assert criterio.passou is False


def test_criterio_sem_diluicao_tolera_numero_de_acoes_identico():
    dados = _dados_empresa_saudavel()
    dados["num_acoes_atual"] = dados["num_acoes_anterior"]  # exatamente igual -> não diluiu -> deve passar
    resultado = piotroski.calcular_piotroski(dados)
    criterio = next(c for c in resultado.criterios if c.chave == "sem_diluicao")
    assert criterio.passou is True


def test_criterio_de_liquidez_exige_melhora_estrita_empate_nao_conta():
    dados = _dados_empresa_saudavel()
    dados["ativo_circulante_atual"] = dados["ativo_circulante_anterior"]
    dados["passivo_circulante_atual"] = dados["passivo_circulante_anterior"]
    resultado = piotroski.calcular_piotroski(dados)
    criterio = next(c for c in resultado.criterios if c.chave == "liquidez_melhorou")
    assert criterio.passou is False


def test_ativos_totais_zero_nao_quebra_e_vira_criterio_nao_avaliado():
    dados = _dados_empresa_saudavel()
    # ativos_totais_atual entra como denominador em TRÊS critérios (ROA,
    # alavancagem e giro de ativos) — os três precisam virar None, não só
    # os dois mais óbvios.
    dados["ativos_totais_atual"] = 0.0
    resultado = piotroski.calcular_piotroski(dados)
    criterio_roa = next(c for c in resultado.criterios if c.chave == "roa_melhorou")
    criterio_alavancagem = next(c for c in resultado.criterios if c.chave == "alavancagem_caiu")
    criterio_giro = next(c for c in resultado.criterios if c.chave == "giro_ativos_melhorou")
    assert criterio_roa.passou is None
    assert criterio_alavancagem.passou is None
    assert criterio_giro.passou is None
    # o resto dos critérios (que não dependem de ativos_totais_atual) continua avaliado normalmente
    assert resultado.total_avaliado == 6


def test_qualidade_do_lucro_exige_caixa_maior_que_lucro_empate_nao_conta():
    dados = _dados_empresa_saudavel()
    dados["fluxo_caixa_operacional_atual"] = dados["lucro_liquido_atual"]  # exatamente igual
    resultado = piotroski.calcular_piotroski(dados)
    criterio = next(c for c in resultado.criterios if c.chave == "qualidade_do_lucro")
    assert criterio.passou is False


def test_classificacao_forte_exige_pelo_menos_8_pontos_com_os_9_avaliados():
    dados = _dados_empresa_saudavel()
    dados["margem_bruta_atual"] = dados["margem_bruta_anterior"]  # derruba 1 critério -> 8/9
    resultado = piotroski.calcular_piotroski(dados)
    assert resultado.pontos == 8
    assert resultado.total_avaliado == 9
    assert resultado.classificacao == "Forte"
