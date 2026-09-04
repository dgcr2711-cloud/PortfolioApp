"""
Aplica no app do PC os pedidos de compra/venda criados pelo celular (ver
mobile-app/src/screens/NovaCompraScreen.tsx).

Fluxo: o celular escreve um "pedido pendente" no Firestore (não mexe nos
seus dados de verdade). Este arquivo lê esses pedidos, VALIDA cada um (o
mesmo tipo de validação que o formulário do PC já faz) e só então adiciona
em dados["compras"] — exatamente como se você tivesse preenchido o
formulário da aba Compras & Vendas você mesmo. Um pedido inválido nunca é
aplicado; ele fica marcado como "erro" e o celular mostra o motivo.

Por que não aplicar na hora, direto do celular? Porque a fonte da verdade
continua sendo só o PC (ver core/cloud_sync.py) — assim nunca existem duas
cópias dos dados podendo divergir.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from core import calculations as calc
from core import cloud_sync, data_store, teses

_PADRAO_TICKER_B3 = re.compile(r"^[A-Z]{4}\d{1,2}$")


def _validar_pendencia(pendencia: dict[str, Any]) -> str | None:
    """Retorna None se o pedido é válido, ou uma mensagem de erro explicando o motivo."""
    ticker = str(pendencia.get("ticker", "")).strip().upper()
    if not _PADRAO_TICKER_B3.match(ticker):
        return f'Ticker "{ticker}" não parece um código válido da B3 (ex: PETR4).'

    quantidade = pendencia.get("quantidade")
    if not isinstance(quantidade, (int, float)) or quantidade <= 0:
        return "Quantidade precisa ser um número maior que zero."

    preco = pendencia.get("precoUnitario")
    if not isinstance(preco, (int, float)) or preco <= 0:
        return "Preço unitário precisa ser um número maior que zero."

    tipo = pendencia.get("tipo")
    if tipo not in ("compra", "venda"):
        return 'Tipo precisa ser "compra" ou "venda".'

    return None


def aplicar_pendencias_do_celular(dados: dict[str, Any], salvar, pendencias: list[dict[str, Any]] | None = None) -> tuple[int, int]:
    """
    Valida e aplica em dados["compras"] (salvando com `salvar`) os pedidos
    pendentes do celular passados em `pendencias` — ou, se `pendencias` for
    None (compatibilidade: nenhum ainda buscado), busca sozinha (2026-09-04:
    normalmente já vem pré-buscada por
    cloud_sync.buscar_pendencias_pendentes_varias_colecoes, chamada uma vez
    só pra todas as 4 coleções em paralelo — ver ui/acoes_comuns.py). Retorna
    (quantidade_aplicada, quantidade_com_erro). Sem pedidos, retorna (0, 0)
    sem fazer nada — seguro de chamar sempre.
    """
    if pendencias is None:
        pendencias = cloud_sync.buscar_pendencias_pendentes()
    if not pendencias:
        return (0, 0)

    aplicadas = 0
    com_erro = 0
    houve_mudanca = False

    for pendencia in pendencias:
        doc_id = pendencia.get("_id")
        erro = _validar_pendencia(pendencia)
        if erro:
            cloud_sync.marcar_pendencia(doc_id, "erro", erro)
            com_erro += 1
            continue

        dados["compras"].append({
            "id": data_store.novo_id(),
            "tipo": pendencia["tipo"],
            "ticker": str(pendencia["ticker"]).strip().upper(),
            "data": date.today().isoformat(),
            "qtd": float(pendencia["quantidade"]),
            "preco": float(pendencia["precoUnitario"]),
            "taxas": 0.0,
        })
        cloud_sync.marcar_pendencia(doc_id, "aplicado")
        aplicadas += 1
        houve_mudanca = True

    if houve_mudanca:
        salvar(dados)

    return (aplicadas, com_erro)


def aplicar_remocoes_do_celular(dados: dict[str, Any], salvar, pendencias: list[dict[str, Any]] | None = None) -> tuple[int, int]:
    """
    Aplica pedidos de remoção de transação criados pela aba Histórico do
    celular (mobile-app/src/screens/HistoricoScreen.tsx) — equivalente a
    clicar em "🗑️ Remover uma transação" na aba Compras & Vendas do PC.
    `pendencias` já pré-buscada (ver aplicar_pendencias_do_celular) ou None
    pra buscar sozinha. Retorna (quantidade_removida, quantidade_com_erro).
    """
    if pendencias is None:
        pendencias = cloud_sync.buscar_pendencias_pendentes(cloud_sync.COLECAO_PENDENCIAS_REMOCOES)
    if not pendencias:
        return (0, 0)

    removidas = 0
    com_erro = 0
    houve_mudanca = False

    for pendencia in pendencias:
        doc_id = pendencia.get("_id")
        compra_id = pendencia.get("compraId")
        existe = any(c["id"] == compra_id for c in dados["compras"])
        if not existe:
            cloud_sync.marcar_pendencia(
                doc_id, "erro", "Essa transação não existe mais (talvez já tenha sido removida no PC).",
                colecao=cloud_sync.COLECAO_PENDENCIAS_REMOCOES,
            )
            com_erro += 1
            continue

        dados["compras"] = [c for c in dados["compras"] if c["id"] != compra_id]
        cloud_sync.marcar_pendencia(doc_id, "aplicado", colecao=cloud_sync.COLECAO_PENDENCIAS_REMOCOES)
        removidas += 1
        houve_mudanca = True

    if houve_mudanca:
        salvar(dados)

    return (removidas, com_erro)


def _validar_pendencia_preco_teto(pendencia: dict[str, Any]) -> str | None:
    """Mesma validação de forma que o formulário FCD do PC exige implicitamente
    (ui/preco_teto.py) — aqui feita explicitamente porque o pedido vem de fora."""
    ticker = str(pendencia.get("ticker", "")).strip().upper()
    if not _PADRAO_TICKER_B3.match(ticker):
        return f'Ticker "{ticker}" não parece um código válido da B3 (ex: WEGE3).'

    campos_numericos = ["fcfBase", "g1Pct", "waccPct", "g2Pct", "dividaLiquida", "margemPct"]
    for campo in campos_numericos:
        if not isinstance(pendencia.get(campo), (int, float)):
            return f'Campo "{campo}" precisa ser um número.'

    anos = pendencia.get("anos")
    if not isinstance(anos, (int, float)) or anos <= 0:
        return "Anos de projeção precisa ser um número maior que zero."

    n_acoes = pendencia.get("nAcoes")
    if not isinstance(n_acoes, (int, float)) or n_acoes <= 0:
        return "Número de ações precisa ser maior que zero."

    return None


def aplicar_calculos_teto_do_celular(dados: dict[str, Any], salvar, pendencias: list[dict[str, Any]] | None = None) -> tuple[int, int]:
    """
    Aplica pedidos de cálculo de Preço Teto (FCD) criados pela aba Preço
    Teto do celular (mobile-app/src/screens/PrecoTetoScreen.tsx) — usa a
    MESMA função calc.calcular_fcd() da calculadora do PC (ui/preco_teto.py),
    então o resultado é sempre idêntico ao que sairia se você tivesse
    preenchido o formulário aqui. `pendencias` já pré-buscada (ver
    aplicar_pendencias_do_celular) ou None pra buscar sozinha. O resultado é
    salvo em dados["precosTeto"][ticker] (aparece na aba Carteira) e também
    devolvido no próprio pedido, para o celular exibir na hora.
    Retorna (quantidade_calculada, quantidade_com_erro).
    """
    if pendencias is None:
        pendencias = cloud_sync.buscar_pendencias_pendentes(cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO)
    if not pendencias:
        return (0, 0)

    calculadas = 0
    com_erro = 0
    houve_mudanca = False

    for pendencia in pendencias:
        doc_id = pendencia.get("_id")
        erro = _validar_pendencia_preco_teto(pendencia)
        if erro:
            cloud_sync.marcar_pendencia(doc_id, "erro", erro, colecao=cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO)
            com_erro += 1
            continue

        ticker = str(pendencia["ticker"]).strip().upper()
        try:
            resultado = calc.calcular_fcd(
                fcf_base=float(pendencia["fcfBase"]),
                g1_pct=float(pendencia["g1Pct"]),
                anos=int(pendencia["anos"]),
                wacc_pct=float(pendencia["waccPct"]),
                g2_pct=float(pendencia["g2Pct"]),
                divida_liquida=float(pendencia["dividaLiquida"]),
                n_acoes=float(pendencia["nAcoes"]),
                margem_pct=float(pendencia["margemPct"]),
            )
        except ValueError as e:
            cloud_sync.marcar_pendencia(doc_id, "erro", str(e), colecao=cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO)
            com_erro += 1
            continue

        dados["precosTeto"][ticker] = {
            "precoTeto": resultado.preco_teto,
            "precoTetoComMargem": resultado.preco_teto_com_margem,
            "atualizadoEm": datetime.now().strftime("%d/%m/%Y"),
        }
        cloud_sync.marcar_pendencia(
            doc_id, "aplicado", colecao=cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO,
            campos_extra={"precoTeto": resultado.preco_teto, "precoTetoComMargem": resultado.preco_teto_com_margem},
        )
        calculadas += 1
        houve_mudanca = True

    if houve_mudanca:
        salvar(dados)

    return (calculadas, com_erro)


def _validar_pendencia_tese(pendencia: dict[str, Any]) -> str | None:
    ticker = str(pendencia.get("ticker", "")).strip().upper()
    if not _PADRAO_TICKER_B3.match(ticker):
        return f'Ticker "{ticker}" não parece um código válido da B3 (ex: PETR4).'

    texto = pendencia.get("texto")
    if not isinstance(texto, str) or not texto.strip():
        return "O texto da tese não pode ficar vazio."
    if len(texto) > teses.LIMITE_CARACTERES_TEXTO:
        return f"O texto da tese não pode passar de {teses.LIMITE_CARACTERES_TEXTO} caracteres."

    return None


def aplicar_teses_do_celular(dados: dict[str, Any], salvar, pendencias: list[dict[str, Any]] | None = None) -> tuple[int, int]:
    """
    Aplica pedidos de nova entrada no Diário de Tese criados pelo celular
    (mobile-app/src/screens/TeseScreen.tsx) — usa a MESMA função
    core.teses.adicionar_entrada() da aba do PC, então uma entrada escrita
    no celular vira uma linha idêntica no diário, com a mesma validação.
    `pendencias` já pré-buscada (ver aplicar_pendencias_do_celular) ou None
    pra buscar sozinha. Retorna (quantidade_aplicada, quantidade_com_erro).
    """
    if pendencias is None:
        pendencias = cloud_sync.buscar_pendencias_pendentes(cloud_sync.COLECAO_PENDENCIAS_TESE)
    if not pendencias:
        return (0, 0)

    aplicadas = 0
    com_erro = 0
    houve_mudanca = False

    for pendencia in pendencias:
        doc_id = pendencia.get("_id")
        erro = _validar_pendencia_tese(pendencia)
        if erro:
            cloud_sync.marcar_pendencia(doc_id, "erro", erro, colecao=cloud_sync.COLECAO_PENDENCIAS_TESE)
            com_erro += 1
            continue

        ticker = str(pendencia["ticker"]).strip().upper()
        try:
            teses.adicionar_entrada(dados, ticker, str(pendencia["texto"]))
        except ValueError as e:
            cloud_sync.marcar_pendencia(doc_id, "erro", str(e), colecao=cloud_sync.COLECAO_PENDENCIAS_TESE)
            com_erro += 1
            continue

        cloud_sync.marcar_pendencia(doc_id, "aplicado", colecao=cloud_sync.COLECAO_PENDENCIAS_TESE)
        aplicadas += 1
        houve_mudanca = True

    if houve_mudanca:
        salvar(dados)

    return (aplicadas, com_erro)
