"""
Monta a lista combinada de ativos (posições reais da carteira + empresas
"alvo" da watchlist que você ainda não comprou) com todos os campos já
calculados — Preço Teto, Margem de Segurança, Indicação, Alerta etc.

Extraído para cá porque tanto a aba "🏠 Visão Geral" quanto a aba
"📈 Carteira" mostram exatamente os mesmos ativos com a mesma lógica de
Preço Teto/Indicação — igual ao dashboard original, que reaproveitava as
mesmas funções `celulaPrecoTeto`/`celulaIndicacao` nas duas telas em vez de
duplicar a lógica.
"""

from __future__ import annotations

from typing import Any

from core import calculations as calc


def montar_lista_ativos(dados: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Retorna uma lista de dicionários, um por ativo (posições reais primeiro,
    depois empresas-alvo), cada um já com:
      - eh_alvo (bool)
      - ticker, setor
      - qtd_total, preco_medio_ponderado, valor_total_investido (None p/ alvo)
      - cotacao_atual, atual, lucro_reais, lucro_pct, variacao_dia_pct (None p/ alvo sem cotação)
      - preco_teto, preco_teto_com_margem, indicacao ("compra"/"neutro"/"venda"/None)
      - motivo_sem_indicacao ("sem_preco_teto" | "sem_cotacao" | None)
      - preco_alvo (alerta configurado, se houver)
    """
    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    tickers_carteira = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_carteira]

    precos_teto = dados["precosTeto"]
    setores = dados["setores"]
    alertas = dados["alertas"]
    cotacoes = dados["cotacoes"]

    lista: list[dict[str, Any]] = []

    for p in posicoes:
        ticker = p["ticker"]
        pt = precos_teto.get(ticker)
        preco_teto = pt["precoTeto"] if pt else None
        ind = calc.indicacao(preco_teto, p["cotacao_atual"])
        motivo = None
        if preco_teto is None:
            motivo = "sem_preco_teto"
        elif p["cotacao_atual"] is None:
            motivo = "sem_cotacao"
        lista.append({
            "eh_alvo": False,
            "ticker": ticker,
            "setor": setores.get(ticker),
            "qtd_total": p["qtd_total"],
            "preco_medio_ponderado": p["preco_medio_ponderado"],
            "valor_total_investido": p["valor_total_investido"],
            "cotacao_atual": p["cotacao_atual"],
            "atual": p["atual"],
            "lucro_reais": p["lucro_reais"],
            "lucro_pct": p["lucro_pct"],
            "variacao_dia_pct": p["variacao_dia_pct"],
            "variacao_dia_reais": p["variacao_dia_reais"],
            "preco_teto": preco_teto,
            "preco_teto_com_margem": calc.preco_com_margem(preco_teto) if preco_teto else None,
            "margem_vs_preco_medio": calc.margem_vs_preco_medio(preco_teto, p["preco_medio_ponderado"]),
            "indicacao": ind,
            "motivo_sem_indicacao": motivo,
            "preco_alvo": alertas.get(ticker),
        })

    for ticker in tickers_alvo:
        pt = precos_teto.get(ticker)
        preco_teto = pt["precoTeto"] if pt else None
        cot = cotacoes.get(ticker)
        cotacao_atual = cot["preco"] if cot else None
        ind = calc.indicacao(preco_teto, cotacao_atual)
        motivo = None
        if preco_teto is None:
            motivo = "sem_preco_teto"
        elif cotacao_atual is None:
            motivo = "sem_cotacao"
        variacao_dia_pct = None
        if cot and cot.get("previousClose") and cotacao_atual is not None:
            variacao_dia_pct = ((cotacao_atual - cot["previousClose"]) / cot["previousClose"]) * 100
        lista.append({
            "eh_alvo": True,
            "ticker": ticker,
            "setor": setores.get(ticker),
            "qtd_total": None,
            "preco_medio_ponderado": None,
            "valor_total_investido": None,
            "cotacao_atual": cotacao_atual,
            "atual": None,
            "lucro_reais": None,
            "lucro_pct": None,
            "variacao_dia_pct": variacao_dia_pct,
            "variacao_dia_reais": None,
            "preco_teto": preco_teto,
            "preco_teto_com_margem": calc.preco_com_margem(preco_teto) if preco_teto else None,
            "margem_vs_preco_medio": None,
            "indicacao": ind,
            "motivo_sem_indicacao": motivo,
            "preco_alvo": alertas.get(ticker),
        })

    return lista


def todos_os_tickers(dados: dict[str, Any]) -> list[str]:
    """Tickers de posições reais + watchlist, sem duplicar — usado para autocompletar campos."""
    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers = {p["ticker"] for p in posicoes}
    tickers.update(dados["watchlist"])
    return sorted(tickers)
