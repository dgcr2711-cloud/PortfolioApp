"""Aba "📅 Proventos" — registro manual de dividendos/JCP/rendimentos e Yield on Cost."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import calculations as calc
from core import data_store
from core.formatting import formatar_data_br, formatar_moeda_priv, formatar_pct


def render(dados: dict, ocultar_valores: bool, salvar) -> None:
    st.title("Proventos Recebidos")
    st.caption("Dividendos, JCP e rendimentos — registrados manualmente")

    total_investido_atual = sum(p["valor_total_investido"] for p in calc.consolidar_posicoes(dados["compras"], dados["eventos"]))
    resumo = calc.resumo_proventos(dados["proventos"], total_investido_atual)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Recebido (histórico)", formatar_moeda_priv(resumo["total_geral"], ocultar_valores))
    c2.metric("Recebido nos últimos 12 meses", formatar_moeda_priv(resumo["total_12m"], ocultar_valores))
    c3.metric("Yield on Cost (12m)", formatar_pct(resumo["yield_on_cost"]))

    st.subheader("Registrar Provento")
    with st.form("form_provento", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        ticker = c1.text_input("Ticker", placeholder="Ex: PETR4", max_chars=10).strip().upper()
        data = c2.date_input("Data")
        tipo = c3.selectbox("Tipo", ["Dividendo", "JCP", "Rendimento"])
        valor = c4.number_input("Valor Total (R$)", min_value=0.0, step=0.01, format="%.2f")
        if st.form_submit_button("Adicionar", type="primary"):
            if not ticker:
                st.warning("Informe o ticker.")
            else:
                dados["proventos"].append({
                    "id": data_store.novo_id(), "ticker": ticker, "data": data.isoformat(),
                    "tipo": tipo, "valor": float(valor),
                })
                salvar(dados)
                st.rerun()

    st.subheader("Histórico de Proventos")
    if not dados["proventos"]:
        st.caption("Nenhum provento registrado ainda.")
        return

    ordenados = sorted(dados["proventos"], key=lambda p: p["data"], reverse=True)
    linhas = [{
        "Data": formatar_data_br(p["data"]), "Ticker": p["ticker"], "Tipo": p["tipo"],
        "Valor": formatar_moeda_priv(p["valor"], ocultar_valores), "id": p["id"],
    } for p in ordenados]
    df = pd.DataFrame(linhas)
    st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

    with st.expander("Remover um provento"):
        opcoes = {f'{l["Data"]} · {l["Ticker"]} · {l["Tipo"]} · {l["Valor"]}': l["id"] for l in linhas}
        escolhida = st.selectbox("Provento", list(opcoes.keys()), key="sel_remover_provento")
        if st.button("Remover provento selecionado"):
            id_remover = opcoes[escolhida]
            dados["proventos"] = [p for p in dados["proventos"] if p["id"] != id_remover]
            salvar(dados)
            st.rerun()
