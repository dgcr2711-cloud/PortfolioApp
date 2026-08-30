"""
Aba "🧾 Compras & Vendas" — histórico de transações, preço médio ponderado
por ativo, eventos societários (desdobramento/grupamento/bonificação),
resultado realizado das vendas e o resumo mensal simplificado de IR.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core import calculations as calc
from core import data_store
from core.formatting import formatar_data_br, formatar_moeda, formatar_moeda_priv
from core.nota_corretagem import extrair_nota_corretagem


def render(dados: dict, ocultar_valores: bool, salvar) -> None:
    st.title("Compras, Vendas & Eventos")
    st.caption("Cada transação alimenta o preço médio ponderado e o resultado realizado da Carteira")

    _formularios(dados, salvar)
    _importar_nota_corretagem(dados, salvar)

    ledger = calc.construir_ledger(dados["compras"], dados["eventos"])
    for aviso in ledger.avisos:
        st.warning(aviso)

    st.subheader("Histórico de Transações")
    _tabela_transacoes(dados, salvar)

    st.subheader("Preço Médio Ponderado por Ativo (posição líquida)")
    _tabela_consolidado(dados)

    st.subheader("🔀 Eventos Societários")
    st.caption(
        "Desdobramento, grupamento ou bonificação — ajustam a quantidade e o preço médio "
        "automaticamente a partir da data informada, sem alterar o custo total investido."
    )
    _tabela_eventos(dados, salvar)

    st.subheader("💰 Resultado Realizado (Vendas)")
    _tabela_resultado_realizado(ledger.resultados_realizados, ocultar_valores)

    st.subheader("🧮 Resumo Mensal para Imposto de Renda")
    st.caption(
        "Estimativa simplificada para ações comuns no mercado à vista: vendas totais até "
        "R$ 20.000/mês são isentas de IR; acima disso, o lucro do mês é estimado a 15%. Não "
        "considera day trade, FIIs, prejuízos de meses anteriores ou outras regras — confirme "
        "sempre com um contador."
    )
    _tabela_resumo_ir(ledger.resultados_realizados, ocultar_valores)


def _formularios(dados: dict, salvar) -> None:
    col1, col2, col3 = st.columns(3)
    with col1.popover("➕ Nova Compra", use_container_width=True):
        _form_transacao(dados, salvar, tipo="compra")
    with col2.popover("➖ Nova Venda", use_container_width=True):
        _form_transacao(dados, salvar, tipo="venda")
    with col3.popover("🔀 Evento Societário", use_container_width=True):
        _form_evento(dados, salvar)


def _form_transacao(dados: dict, salvar, tipo: str) -> None:
    rotulo = "Venda" if tipo == "venda" else "Compra"
    with st.form(f"form_{tipo}", clear_on_submit=True):
        ticker = st.text_input("Ticker", placeholder="Ex: PETR4", max_chars=10).strip().upper()
        data = st.date_input("Data")
        col_a, col_b = st.columns(2)
        qtd = col_a.number_input("Quantidade", min_value=1, step=1)
        preco = col_b.number_input(f"Preço Unit. de {rotulo} (R$)", min_value=0.0, step=0.01, format="%.2f")
        taxas = st.number_input("Taxas / Corretagem (R$, opcional)", min_value=0.0, step=0.01, format="%.2f")
        if st.form_submit_button(f"Salvar {rotulo}", type="primary"):
            if not ticker:
                st.warning("Informe o ticker.")
            else:
                dados["compras"].append({
                    "id": data_store.novo_id(), "tipo": tipo, "ticker": ticker,
                    "data": data.isoformat(), "qtd": float(qtd), "preco": float(preco), "taxas": float(taxas),
                })
                salvar(dados)
                st.rerun()


def _form_evento(dados: dict, salvar) -> None:
    with st.form("form_evento", clear_on_submit=True):
        ticker = st.text_input("Ticker", placeholder="Ex: PETR4", max_chars=10).strip().upper()
        data = st.date_input("Data do Evento")
        tipo = st.selectbox("Tipo", ["desdobramento", "grupamento", "bonificacao"], format_func=lambda t: {
            "desdobramento": "Desdobramento (Split)", "grupamento": "Grupamento (Inplit)", "bonificacao": "Bonificação em Ações",
        }[t])
        col_a, col_b = st.columns(2)
        de = col_a.number_input("Proporção — de", min_value=0.0001, value=1.0, step=1.0)
        para = col_b.number_input("Proporção — para", min_value=0.0001, value=2.0, step=1.0)
        st.caption("Exemplos: desdobramento 1→2 dobra sua quantidade; grupamento 10→1 junta cada 10 ações em 1; bonificação de 10% = de 100 para 110.")
        if st.form_submit_button("Salvar Evento", type="primary"):
            if not ticker:
                st.warning("Informe o ticker.")
            else:
                dados["eventos"].append({
                    "id": data_store.novo_id(), "ticker": ticker, "data": data.isoformat(),
                    "tipo": tipo, "de": de, "para": para, "fator": para / de,
                })
                salvar(dados)
                st.rerun()


def _importar_nota_corretagem(dados: dict, salvar) -> None:
    """Lê automaticamente ticker/data/quantidade/preço/taxas de um PDF de nota
    de corretagem (ver core/nota_corretagem.py) e mostra os dados numa tela
    de conferência — nada é salvo na carteira sem você revisar e confirmar
    primeiro, exatamente pra cobrir os casos em que a leitura do PDF vier
    incompleta ou errada (o formato varia de corretora pra corretora)."""
    with st.expander("📎 Importar Nota de Corretagem (PDF)"):
        st.caption(
            "Envie o PDF da nota e o app tenta preencher ticker, quantidade, preço e taxas "
            "sozinho. Testado com notas da BTG Pactual — outras corretoras usam um formato "
            "parecido (é padronizado pela B3), mas sempre confira os valores antes de confirmar."
        )
        versao_uploader = st.session_state.get("nota_corretagem_versao_uploader", 0)
        arquivo = st.file_uploader("PDF da nota", type=["pdf"], key=f"upload_nota_corretagem_{versao_uploader}")
        if arquivo is None:
            return

        resultado = extrair_nota_corretagem(arquivo.getvalue())

        for aviso in resultado.avisos:
            st.warning(aviso)

        if not resultado.transacoes:
            return

        if resultado.corretora:
            st.caption(f"Corretora identificada: {resultado.corretora}")

        data_negociacao = st.date_input(
            "Data da negociação",
            value=date.fromisoformat(resultado.data) if resultado.data else date.today(),
            key="nota_corretagem_data",
        )

        st.write("Confira os dados abaixo antes de confirmar — corrija qualquer campo se precisar:")
        tabela_editavel = pd.DataFrame([{
            "Tipo": t.tipo, "Ticker": t.ticker, "Quantidade": t.qtd,
            "Preço Unit.": t.preco, "Taxas": t.taxas,
        } for t in resultado.transacoes])
        editado = st.data_editor(
            tabela_editavel,
            column_config={"Tipo": st.column_config.SelectboxColumn(options=["compra", "venda"])},
            hide_index=True,
            use_container_width=True,
            key="nota_corretagem_editor",
        )

        if st.button("✅ Confirmar e adicionar à carteira", type="primary"):
            for _, linha in editado.iterrows():
                dados["compras"].append({
                    "id": data_store.novo_id(),
                    "tipo": linha["Tipo"],
                    "ticker": str(linha["Ticker"]).strip().upper(),
                    "data": data_negociacao.isoformat(),
                    "qtd": float(linha["Quantidade"]),
                    "preco": float(linha["Preço Unit."]),
                    "taxas": float(linha["Taxas"]),
                })
            salvar(dados)
            # Troca a "versão" do uploader pra forçar o Streamlit a mostrar o
            # campo de upload vazio de novo, em vez de reprocessar o mesmo PDF.
            st.session_state["nota_corretagem_versao_uploader"] = versao_uploader + 1
            st.success(f"{len(editado)} transação(ões) adicionada(s) a partir da nota.")
            st.rerun()


def _tabela_transacoes(dados: dict, salvar) -> None:
    compras = dados["compras"]
    if not compras:
        st.caption("Nenhuma transação registrada ainda.")
        return
    ordenadas = sorted(compras, key=lambda c: c["data"], reverse=True)
    linhas = []
    for c in ordenadas:
        # Registros importados de versões bem antigas do dashboard não tinham
        # o campo "tipo" (só existiam compras, vendas vieram depois) — trata
        # a ausência como "compra", igual ao dashboard original sempre fez.
        tipo = c.get("tipo", "compra")
        total = (c["qtd"] * c["preco"]) - (c.get("taxas") or 0) if tipo == "venda" else (c["qtd"] * c["preco"]) + (c.get("taxas") or 0)
        linhas.append({
            "Data": formatar_data_br(c["data"]), "Tipo": "🔴 Venda" if tipo == "venda" else "🟢 Compra",
            "Ticker": c["ticker"], "Qtd": c["qtd"], "Preço Unit.": formatar_moeda(c["preco"]),
            "Taxas": formatar_moeda(c.get("taxas") or 0), "Total": formatar_moeda(total), "id": c["id"],
        })
    df = pd.DataFrame(linhas)
    st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

    with st.expander("🗑️ Remover uma transação"):
        opcoes = {f'{l["Data"]} · {l["Tipo"]} · {l["Ticker"]} · {l["Qtd"]}x': l["id"] for l in linhas}
        escolhida = st.selectbox("Transação", list(opcoes.keys()), key="sel_remover_transacao")
        if st.button("Remover transação selecionada"):
            id_remover = opcoes[escolhida]
            dados["compras"] = [c for c in dados["compras"] if c["id"] != id_remover]
            salvar(dados)
            st.rerun()


def _tabela_consolidado(dados: dict) -> None:
    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    if not posicoes:
        st.caption("Nenhuma posição em aberto.")
        return
    linhas = [{
        "Ticker": p["ticker"], "Qtd Total": p["qtd_total"],
        "Valor Investido": formatar_moeda(p["valor_total_investido"]),
        "Preço Médio": formatar_moeda(p["preco_medio_ponderado"]),
        "Setor": dados["setores"].get(p["ticker"], "—"),
    } for p in posicoes]
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)


def _tabela_eventos(dados: dict, salvar) -> None:
    eventos = dados["eventos"]
    if not eventos:
        st.caption("Nenhum evento societário registrado ainda.")
        return
    rotulos_tipo = {"desdobramento": "Desdobramento", "grupamento": "Grupamento", "bonificacao": "Bonificação"}
    ordenados = sorted(eventos, key=lambda e: e["data"], reverse=True)
    linhas = [{
        "Data": formatar_data_br(e["data"]), "Ticker": e["ticker"], "Tipo": rotulos_tipo.get(e["tipo"], e["tipo"]),
        "Proporção": f'{e["de"]:g} → {e["para"]:g}', "Fator": f'{e["fator"]:.4f}', "id": e["id"],
    } for e in ordenados]
    df = pd.DataFrame(linhas)
    st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)
    with st.expander("Remover um evento"):
        opcoes = {f'{l["Data"]} · {l["Ticker"]} · {l["Tipo"]}': l["id"] for l in linhas}
        escolhida = st.selectbox("Evento", list(opcoes.keys()), key="sel_remover_evento")
        if st.button("Remover evento selecionado"):
            id_remover = opcoes[escolhida]
            dados["eventos"] = [e for e in dados["eventos"] if e["id"] != id_remover]
            salvar(dados)
            st.rerun()


def _tabela_resultado_realizado(resultados: list[dict], ocultar_valores: bool) -> None:
    if not resultados:
        st.caption("Nenhuma venda registrada ainda.")
        return
    ordenados = sorted(resultados, key=lambda r: r["data"], reverse=True)
    linhas = [{
        "Data": formatar_data_br(r["data"]), "Ticker": r["ticker"], "Qtd": round(r["qtd"], 4),
        "Preço Venda": formatar_moeda(r["preco_venda"]), "Custo Base": formatar_moeda_priv(r["custo_base"], ocultar_valores),
        "Lucro/Prejuízo": ("+" if r["lucro"] >= 0 else "") + formatar_moeda_priv(r["lucro"], ocultar_valores),
    } for r in ordenados]
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)


def _tabela_resumo_ir(resultados: list[dict], ocultar_valores: bool) -> None:
    resumo = calc.resumo_ir_mensal(resultados)
    if not resumo:
        st.caption("Nenhuma venda registrada ainda.")
        return
    linhas = [{
        "Mês": r["mes"], "Total Vendido": formatar_moeda_priv(r["total_vendido"], ocultar_valores),
        "Lucro/Prejuízo": formatar_moeda_priv(r["lucro"], ocultar_valores),
        "Situação": "✅ Isento (≤ R$ 20.000)" if r["isento"] else "⚠️ Sujeito a IR",
        "IR Estimado (DARF)": formatar_moeda(r["imposto_estimado"]) if r["imposto_estimado"] > 0 else "—",
    } for r in resumo]
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
