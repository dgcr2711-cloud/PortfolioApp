"""
Aba "🎯 Preço Teto" — calculadora de Fluxo de Caixa Descontado (2 estágios)
e lista dos preços-teto já salvos, que alimentam a coluna "Indicação" da
Carteira. A extração automática de PDFs de release do dashboard original
não foi trazida nesta primeira versão (dependia de pdf.js rodando no
navegador) — os valores continuam sendo preenchidos manualmente, com os
mesmos links diretos de RI como apoio.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import calculations as calc
from core.config import LINKS_RI
from core.formatting import formatar_moeda


def render(dados: dict, salvar) -> None:
    st.title("Preço Teto — Fluxo de Caixa Descontado")
    st.caption(
        "Modelo simplificado de 2 estágios (FCD). Ao calcular, o resultado é salvo e "
        "aparece automaticamente na aba Carteira."
    )

    col_form, col_resultado = st.columns([1, 2])

    with col_form:
        st.subheader("Premissas")
        with st.form("form_fcd"):
            ticker = st.text_input("Ticker", placeholder="Ex: WEGE3", max_chars=10).strip().upper()
            fcf_base = st.number_input("FCF do último ano (R$ milhões)", step=0.01, format="%.2f")
            c1, c2 = st.columns(2)
            g1 = c1.number_input("Cresc. explícito g1 (%)", step=0.01, format="%.2f")
            anos = c2.number_input("Anos de projeção", min_value=1, max_value=15, value=5, step=1)
            c3, c4 = st.columns(2)
            wacc = c3.number_input("Taxa de desconto / WACC (%)", step=0.01, format="%.2f")
            g2 = c4.number_input("Cresc. perpetuidade g2 (%)", step=0.01, format="%.2f")
            c5, c6 = st.columns(2)
            divida = c5.number_input("Dívida líquida (R$ mi)", value=0.0, step=0.01, format="%.2f")
            n_acoes = c6.number_input("Nº ações (milhões)", step=0.01, format="%.2f")
            margem = st.number_input("Margem de segurança desejada (%)", value=20.0, step=0.01, format="%.2f")
            calcular = st.form_submit_button("Calcular Preço Teto", type="primary")

        if ticker and ticker in LINKS_RI:
            st.caption(f"🔗 RI de {ticker}: {LINKS_RI[ticker]}")

    with col_resultado:
        st.subheader("Resultado")
        if calcular:
            if n_acoes <= 0:
                st.error("Informe o número de ações (deve ser maior que zero).")
            else:
                try:
                    resultado = calc.calcular_fcd(fcf_base, g1, int(anos), wacc, g2, divida, n_acoes, margem)
                except ValueError as e:
                    st.error(str(e))
                else:
                    c1, c2 = st.columns(2)
                    c1.metric("Preço Teto", formatar_moeda(resultado.preco_teto))
                    c2.metric(f"Preço Teto c/ margem de {margem:g}%", formatar_moeda(resultado.preco_teto_com_margem))
                    st.markdown(
                        f"- Valor presente dos fluxos: **{formatar_moeda(resultado.vp_fluxos)} mi**\n"
                        f"- Valor presente terminal: **{formatar_moeda(resultado.vp_terminal)} mi**\n"
                        f"- Valor da empresa: **{formatar_moeda(resultado.valor_empresa)} mi**\n"
                        f"- Valor do equity: **{formatar_moeda(resultado.valor_equity)} mi**"
                    )
                    with st.expander("Ver projeção ano a ano"):
                        df_proj = pd.DataFrame([
                            {"Período": f"Ano {p['ano']}", "FCF proj.": formatar_moeda(p["fcf"]) + " mi", "VP": formatar_moeda(p["vp"]) + " mi"}
                            for p in resultado.projecao
                        ])
                        st.dataframe(df_proj, use_container_width=True, hide_index=True)

                    if ticker:
                        dados["precosTeto"][ticker] = {
                            "precoTeto": resultado.preco_teto,
                            "precoTetoComMargem": resultado.preco_teto_com_margem,
                            "atualizadoEm": pd.Timestamp.now().strftime("%d/%m/%Y"),
                        }
                        salvar(dados)
                        st.success(f"✅ Salvo. Este preço teto agora aparece na aba Carteira para {ticker}.")
                    else:
                        st.warning("Informe um ticker para salvar este resultado e vê-lo na Carteira.")
        else:
            st.info('Preencha as premissas ao lado e clique em "Calcular Preço Teto".')

        st.subheader("Preços Teto já calculados")
        _tabela_precos_teto(dados, salvar)

    st.markdown("---")
    with st.expander("⚠️ Sobre buscar press releases automaticamente"):
        st.write(
            "Os releases/ITRs de cada empresa geralmente são divulgados em PDF nos sites de "
            "Relações com Investidores — não há uma forma automática e confiável de ler esses "
            "números direto por aqui. Os campos acima continuam manuais; use os links de RI "
            "abaixo como apoio."
        )
        for tk, link in sorted(LINKS_RI.items()):
            st.caption(f"**{tk}**: {link}")


def _tabela_precos_teto(dados: dict, salvar) -> None:
    precos_teto = dados["precosTeto"]
    if not precos_teto:
        st.caption("Nenhum preço teto calculado ainda.")
        return
    linhas = [{
        "Ticker": ticker, "Preço Teto": formatar_moeda(v["precoTeto"]),
        "Com Margem": formatar_moeda(v["precoTetoComMargem"]), "Calculado em": v.get("atualizadoEm", "—"),
    } for ticker, v in precos_teto.items()]
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

    with st.expander("Remover um preço teto"):
        ticker_remover = st.selectbox("Ativo", list(precos_teto.keys()), key="sel_remover_preco_teto")
        if st.button("Remover preço teto selecionado"):
            del dados["precosTeto"][ticker_remover]
            salvar(dados)
            st.rerun()
