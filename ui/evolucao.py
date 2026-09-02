"""
Aba "📊 Evolução" — patrimônio ao longo do tempo (um snapshot é salvo toda
vez que você clica em "Atualizar Cotações" na Carteira) e o comparativo
com o Ibovespa usando retorno ponderado pelo tempo (aproximação de TWR).
"""

from __future__ import annotations

from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from core import calculations as calc
from core import risco
from core.formatting import formatar_data_br, formatar_pct
from ui.styles import card_kpi_html, render_cards


def render(dados: dict, salvar) -> None:
    st.title("Evolução Patrimonial")
    st.caption("Um registro (snapshot) é salvo automaticamente sempre que você atualiza cotações")

    if st.button("📌 Registrar snapshot de hoje"):
        _registrar_snapshot_manual(dados, salvar)

    historico = dados["historico"]
    st.subheader("Patrimônio ao longo do tempo")
    if not historico:
        st.info("Ainda não há snapshots suficientes. Atualize as cotações em dias diferentes para começar a ver a evolução aqui.")
    else:
        fig = go.Figure()
        datas = [formatar_data_br(h["data"]) for h in historico]
        fig.add_trace(go.Scatter(
            x=datas, y=[h["totalAtual"] for h in historico], name="Patrimônio Atual",
            line=dict(color="#34d399", width=2), fill="tozeroy", fillcolor="rgba(52,211,153,0.1)",
        ))
        fig.add_trace(go.Scatter(
            x=datas, y=[h["totalInvestido"] for h in historico], name="Total Investido",
            line=dict(color="#9ca3af", width=2, dash="dash"),
        ))
        fig.update_layout(
            height=320, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color="#9ca3af")),
            xaxis=dict(color="#9ca3af", gridcolor="rgba(156,163,175,0.1)"),
            yaxis=dict(color="#9ca3af", gridcolor="rgba(156,163,175,0.1)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.subheader("🆚 Comparativo com o Ibovespa")
    st.caption(
        "A carteira usa retorno ponderado pelo tempo (aproximado): a variação do total investido "
        "entre snapshots é tratada como aporte/retirada, para não misturar 'ganho de mercado' com "
        "'dinheiro novo colocado'. O Ibovespa usa retorno simples do período."
    )
    comparativo = calc.twr_vs_ibovespa(historico)
    if comparativo:
        cor_cart = "#34d399" if comparativo["rent_carteira_pct"] >= 0 else "#fb7185"
        cor_ibov = "#34d399" if comparativo["rent_ibov_pct"] >= 0 else "#fb7185"
        render_cards([
            card_kpi_html(
                "Sua carteira no período (TWR aprox.)",
                formatar_pct(comparativo["rent_carteira_pct"]), cor_valor=cor_cart,
            ),
            card_kpi_html(
                "Ibovespa no mesmo período",
                formatar_pct(comparativo["rent_ibov_pct"]), cor_valor=cor_ibov,
            ),
        ])
        st.caption(
            f"Período: {formatar_data_br(comparativo['data_inicio'])} até {formatar_data_br(comparativo['data_fim'])}. "
            "Metodologia: retorno da carteira encadeado por sub-período (aproximação de TWR); Ibovespa em retorno simples."
        )
    else:
        render_cards([
            card_kpi_html("Sua carteira no período (TWR aprox.)", "—"),
            card_kpi_html("Ibovespa no mesmo período", "—"),
        ])
        st.caption("Atualize as cotações em ao menos 2 dias diferentes para ver este comparativo (o Ibovespa é buscado junto com suas cotações).")

    _secao_risco(dados, salvar)


def _secao_risco(dados: dict, salvar) -> None:
    st.subheader("📐 Risco da Carteira (Beta e Sharpe)")
    st.caption(
        "Aproximado a partir dos MESMOS snapshots do gráfico acima — não é uma série diária "
        "de verdade, então quanto mais irregular o ritmo de atualização, menos preciso o número. "
        "Veja a explicação completa em core/risco.py."
    )

    taxa_atual = dados.get("taxaLivreRiscoAnualPct", 10.0)
    taxa_nova = st.number_input(
        "Taxa livre de risco anual (%) — ex: a Selic/CDI do período",
        min_value=0.0, max_value=100.0, value=float(taxa_atual), step=0.25,
        help="Usada só no cálculo do Sharpe. O app não busca isso sozinho — confira a Selic/CDI vigente e ajuste aqui.",
    )
    if taxa_nova != taxa_atual:
        dados["taxaLivreRiscoAnualPct"] = taxa_nova
        salvar(dados)

    resultado = risco.calcular_risco_carteira(dados["historico"], taxa_nova)
    if resultado.aviso:
        st.info(resultado.aviso)
        return

    valor_beta = f"{resultado.beta:.2f}" if resultado.beta is not None else "—"
    valor_sharpe = f"{resultado.sharpe_anualizado:.2f}" if resultado.sharpe_anualizado is not None else "—"
    render_cards([
        card_kpi_html("Beta (vs. Ibovespa)", valor_beta),
        card_kpi_html("Índice de Sharpe (anualizado)", valor_sharpe),
    ])
    if resultado.beta is None:
        st.caption("Beta: Ibovespa não variou no período coberto pelos snapshots — não dá para calcular.")
    if resultado.sharpe_anualizado is None:
        st.caption("Sharpe: carteira sem nenhuma variação de retorno entre os períodos — não dá para calcular.")

    with st.expander("O que isso significa?"):
        st.markdown(
            "- **Beta**: o quanto a carteira costuma se mover em relação ao Ibovespa. "
            "1 = se move junto; acima de 1 = mais volátil que o mercado; abaixo de 1 = menos volátil; "
            "negativo = tende a se mover na direção oposta (raro).\n"
            "- **Sharpe**: retorno em excesso sobre a taxa livre de risco, dividido pela volatilidade "
            "da carteira. Quanto maior, melhor o retorno obtido por unidade de risco assumido — não é "
            "a mesma coisa que 'quanto rendeu'."
        )


def _registrar_snapshot_manual(dados: dict, salvar) -> None:
    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    if not posicoes:
        st.warning("Registre ao menos uma posição antes de criar um snapshot.")
        return
    total_investido = sum(p["valor_total_investido"] for p in posicoes)
    total_atual = sum(p["atual"] for p in posicoes)
    hoje = datetime.now().strftime("%Y-%m-%d")
    existente = next((h for h in dados["historico"] if h["data"] == hoje), None)
    if existente:
        existente["totalInvestido"] = total_investido
        existente["totalAtual"] = total_atual
    else:
        dados["historico"].append({"data": hoje, "totalInvestido": total_investido, "totalAtual": total_atual, "ibov": None})
    dados["historico"].sort(key=lambda h: h["data"])
    salvar(dados)
    st.rerun()
