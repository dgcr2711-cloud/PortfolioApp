"""
Aba "⚙️ Configurações" — alertas de preço-alvo, lista de observação
(watchlist) e backup dos dados (exportar/importar .json).

Diferente do dashboard em HTML (dados presos ao localStorage de um
navegador específico), aqui os dados já ficam salvos em disco a cada
alteração (core/data_store.py) — a exportação serve principalmente para
guardar uma cópia externa (pendrive, nuvem) ou migrar para outro
computador.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core import data_store
from core.formatting import formatar_moeda
from ui import exportacao


def render(dados: dict, salvar) -> None:
    st.title("Configurações")
    st.caption("Alertas de preço, lista de observação e backup dos dados")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔔 Alertas de Preço-Alvo")
        with st.form("form_alerta", clear_on_submit=True):
            c1, c2 = st.columns(2)
            ticker = c1.text_input("Ticker", max_chars=10).strip().upper()
            preco_alvo = c2.number_input("Preço Alvo (R$)", min_value=0.0, step=0.01, format="%.2f")
            if st.form_submit_button("Salvar Alerta"):
                if ticker:
                    dados["alertas"][ticker] = preco_alvo
                    salvar(dados)
                    st.rerun()

        if dados["alertas"]:
            for ticker, preco in list(dados["alertas"].items()):
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{ticker}** — {formatar_moeda(preco)}")
                if c2.button("Remover", key=f"rm_alerta_{ticker}"):
                    del dados["alertas"][ticker]
                    salvar(dados)
                    st.rerun()
        else:
            st.caption("Nenhum alerta configurado.")

        st.subheader("👀 Lista de Observação (Watchlist)")
        with st.form("form_watchlist_config", clear_on_submit=True):
            novo_ticker = st.text_input("Adicionar ticker", placeholder="Ex: TAEE11", max_chars=10).strip().upper()
            if st.form_submit_button("Adicionar à lista"):
                if novo_ticker and novo_ticker not in dados["watchlist"]:
                    dados["watchlist"].append(novo_ticker)
                    salvar(dados)
                    st.rerun()

        if dados["watchlist"]:
            for ticker in list(dados["watchlist"]):
                c1, c2 = st.columns([4, 1])
                c1.write(ticker)
                if c2.button("Remover", key=f"rm_watch_{ticker}"):
                    dados["watchlist"].remove(ticker)
                    salvar(dados)
                    st.rerun()
        else:
            st.caption("Lista de observação vazia.")

    with col2:
        st.subheader("💾 Backup dos Dados")
        st.caption(
            "Seus dados já ficam salvos automaticamente em data/portfolio_data.json a cada "
            "alteração. Exporte periodicamente para guardar uma cópia extra (pendrive, nuvem) "
            "ou migrar para outro computador."
        )
        conteudo_json = data_store.exportar_dados_json(dados)
        st.download_button(
            "⬇️ Exportar dados (.json)", data=conteudo_json,
            file_name=f"backup-portfolio-{datetime.now().strftime('%Y-%m-%d')}.json",
            mime="application/json", use_container_width=True,
        )

        arquivo = st.file_uploader("⬆️ Importar dados (.json)", type=["json"])
        if arquivo is not None:
            st.warning(
                "Importar substitui TODOS os dados atuais do app (compras, vendas, proventos, "
                "preços-teto, watchlist etc.). Um backup automático dos dados atuais é feito antes."
            )
            if st.button("Confirmar importação", type="primary"):
                try:
                    novos_dados = data_store.importar_dados_json(arquivo.getvalue())
                except Exception as e:
                    st.error(f"Não foi possível importar: {e}")
                else:
                    data_store.fazer_backup_automatico(dados)
                    salvar(novos_dados)
                    st.success("Dados importados com sucesso!")
                    st.rerun()

        st.subheader("📤 Exportar para Excel/CSV")
        st.caption(
            "Diferente do backup em .json (que serve para restaurar os dados neste app), isto aqui "
            "é para abrir numa planilha, mandar para um contador, ou analisar por conta própria."
        )
        try:
            excel_bytes = exportacao.gerar_excel_carteira(dados)
            st.download_button(
                "⬇️ Exportar Carteira Completa (.xlsx)", data=excel_bytes,
                file_name=f"carteira-b3-{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Um arquivo com 4 abas: Posições, Proventos, Compras e Vendas, e Resumo IR Mensal.",
            )
        except ImportError:
            st.caption(
                "⚠️ Para exportar em .xlsx, instale a biblioteca que falta rodando "
                "`pip install -r requirements.txt` com o app fechado, e abra o app de novo."
            )

        csv_texto = exportacao.gerar_csv_posicoes(dados)
        st.download_button(
            "⬇️ Exportar só as Posições (.csv)", data=csv_texto,
            file_name=f"posicoes-b3-{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv", use_container_width=True,
        )

        st.subheader("🎨 Sobre o tema")
        st.caption(
            "O tema escuro (cores de fundo e destaque) é definido em `.streamlit/config.toml` — "
            "edite esse arquivo se quiser trocar as cores do app inteiro de uma vez."
        )
