"""
Exportação da carteira para Excel (.xlsx, com várias abas) e CSV — pedido
explícito da auditoria (item "Exportação para Excel/CSV"): poder levar os
números para uma planilha própria, mandar para um contador, ou só ter uma
cópia "olhável" fora do app.

Fica em ui/ (não em core/) porque usa ui.ativos.montar_lista_ativos — core/
nunca importa de ui/, só o contrário, para manter core/ testável sozinho e
sem depender de nada além de Python puro.

Usa pandas (já é dependência do projeto) + openpyxl para escrever o .xlsx.
Este módulo só formata o que core/calculations.py e core/imposto_renda.py já
calculam — nenhuma conta nova é feita aqui.
"""

from __future__ import annotations

import io
from typing import Any

import pandas as pd

from core import calculations as calc
from core import imposto_renda as ir
from ui.ativos import montar_lista_ativos

COLUNAS_POSICOES = {
    "ticker": "Ticker",
    "setor": "Setor",
    "eh_alvo": "É empresa-alvo (não comprada ainda)",
    "qtd_total": "Quantidade",
    "preco_medio_ponderado": "Preço Médio (R$)",
    "cotacao_atual": "Cotação Atual (R$)",
    "variacao_dia_pct": "Variação do Dia (%)",
    "preco_teto": "Preço Teto (R$)",
    "preco_teto_com_margem": "Preço Teto com Margem 20% (R$)",
    "indicacao": "Indicação",
    "margem_vs_preco_medio": "Margem vs Preço Médio (%)",
    "valor_total_investido": "Total Investido (R$)",
    "atual": "Total Atual (R$)",
    "lucro_reais": "Resultado (R$)",
    "lucro_pct": "Resultado (%)",
}


def montar_dataframe_posicoes(dados: dict[str, Any]) -> pd.DataFrame:
    """Uma linha por ativo (posições reais + empresas-alvo da watchlist), mesmos campos da tabela da aba Carteira."""
    lista = montar_lista_ativos(dados)
    if not lista:
        return pd.DataFrame(columns=list(COLUNAS_POSICOES.values()))
    df = pd.DataFrame(lista)[list(COLUNAS_POSICOES.keys())]
    df = df.rename(columns=COLUNAS_POSICOES)
    return df


def montar_dataframe_proventos(dados: dict[str, Any]) -> pd.DataFrame:
    """Uma linha por provento recebido (dividendo, JCP, rendimento de FII etc.), mais recente primeiro."""
    proventos = dados.get("proventos", [])
    if not proventos:
        return pd.DataFrame(columns=["Data", "Ticker", "Tipo", "Valor (R$)"])
    df = pd.DataFrame(proventos)
    df = df.rename(columns={"data": "Data", "ticker": "Ticker", "tipo": "Tipo", "valor": "Valor (R$)"})
    colunas = [c for c in ["Data", "Ticker", "Tipo", "Valor (R$)"] if c in df.columns]
    df = df[colunas].sort_values("Data", ascending=False, na_position="last")
    return df


def montar_dataframe_transacoes(dados: dict[str, Any]) -> pd.DataFrame:
    """Uma linha por compra/venda registrada, mais recente primeiro."""
    compras = dados.get("compras", [])
    if not compras:
        return pd.DataFrame(columns=["Data", "Ticker", "Tipo", "Quantidade", "Preço (R$)", "Taxas (R$)"])
    df = pd.DataFrame(compras)
    df = df.rename(columns={
        "data": "Data", "ticker": "Ticker", "tipo": "Tipo",
        "qtd": "Quantidade", "preco": "Preço (R$)", "taxas": "Taxas (R$)",
    })
    colunas = [c for c in ["Data", "Ticker", "Tipo", "Quantidade", "Preço (R$)", "Taxas (R$)"] if c in df.columns]
    df = df[colunas].sort_values("Data", ascending=False, na_position="last")
    return df


def montar_dataframe_resumo_ir(dados: dict[str, Any]) -> pd.DataFrame:
    """
    Resumo mensal de Imposto de Renda (Swing + Day Trade já separados,
    prejuízo compensado, DARF a pagar) — mesma lógica de core/imposto_renda.py
    usada na aba "🏛️ Imposto de Renda", mais recente primeiro.
    """
    resultado = ir.construir_resultados_ir(dados.get("compras", []), dados.get("eventos", []))
    linhas_mensais = ir.resumo_mensal_ir(resultado)
    if not linhas_mensais:
        return pd.DataFrame(columns=[
            "Mês", "Lucro Swing (R$)", "Isento (Swing)", "Lucro Day Trade (R$)",
            "Imposto Devido no Mês (R$)", "DARF a Pagar (R$)", "Abaixo do Mínimo de R$10",
        ])
    linhas = []
    for m in linhas_mensais:
        linhas.append({
            "Mês": m["mes"],
            "Lucro Swing (R$)": m["swing"]["lucro"],
            "Isento (Swing)": "Sim" if m["swing"]["isento"] else "Não",
            "Lucro Day Trade (R$)": m["day_trade"]["lucro"],
            "Imposto Devido no Mês (R$)": m["imposto_devido_mes"],
            "DARF a Pagar (R$)": m["darf_a_pagar"],
            "Abaixo do Mínimo de R$10": "Sim" if m["abaixo_do_minimo"] else "Não",
        })
    df = pd.DataFrame(linhas).sort_values("Mês", ascending=False)
    return df


def gerar_csv_posicoes(dados: dict[str, Any]) -> str:
    """CSV simples (separador ';', igual ao padrão do Excel em português) só com as posições."""
    df = montar_dataframe_posicoes(dados)
    return df.to_csv(index=False, sep=";", decimal=",")


def gerar_csv_proventos(dados: dict[str, Any]) -> str:
    """CSV simples (separador ';', igual ao padrão do Excel em português) só com o histórico de proventos."""
    df = montar_dataframe_proventos(dados)
    return df.to_csv(index=False, sep=";", decimal=",")


def gerar_excel_carteira(dados: dict[str, Any]) -> bytes:
    """
    Um único arquivo .xlsx com 4 abas: Posições, Proventos, Compras e Vendas,
    e Resumo IR Mensal — pronto para abrir no Excel/Google Sheets ou mandar
    para um contador.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        montar_dataframe_posicoes(dados).to_excel(escritor, sheet_name="Posições", index=False)
        montar_dataframe_proventos(dados).to_excel(escritor, sheet_name="Proventos", index=False)
        montar_dataframe_transacoes(dados).to_excel(escritor, sheet_name="Compras e Vendas", index=False)
        montar_dataframe_resumo_ir(dados).to_excel(escritor, sheet_name="Resumo IR Mensal", index=False)

        # Largura de coluna automática (aproximada, pelo maior conteúdo de cada
        # coluna) — evita abrir o arquivo e ver tudo cortado em "###" ou truncado.
        for aba in escritor.sheets.values():
            for coluna in aba.columns:
                maior_conteudo = max((len(str(celula.value)) for celula in coluna if celula.value is not None), default=8)
                letra_coluna = coluna[0].column_letter
                aba.column_dimensions[letra_coluna].width = min(maior_conteudo + 2, 40)

    return buffer.getvalue()
