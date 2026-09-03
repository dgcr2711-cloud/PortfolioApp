"""
Gráficos (plotly) compartilhados entre abas — extraído em 2026-09-03 para
que a Visão Geral pudesse ganhar os mesmos gráficos de Alocação (antes só
em 📈 Carteira) e Evolução Patrimonial (antes só em 📊 Evolução) sem
duplicar a definição de cores/estilo em três lugares. `ui/carteira.py` e
`ui/evolucao.py` foram atualizados para importar daqui — o visual de
nenhuma das duas abas mudou, só a origem do código.
"""

from __future__ import annotations

import plotly.graph_objects as go

from core.formatting import formatar_data_br

PALETA_ALOCACAO = ["#34d399", "#38bdf8", "#fbbf24", "#a78bfa", "#fb7185", "#22d3ee", "#f472b6", "#a3e635", "#fb923c", "#94a3b8"]


def grafico_alocacao(labels: list[str], valores: list[float], *, altura: int = 300) -> go.Figure:
    """Donut de alocação (por ativo ou por setor) — mesmo visual usado em 📈 Carteira."""
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=valores, hole=0.55,
        marker=dict(colors=PALETA_ALOCACAO, line=dict(color="#111827", width=2)),
        textinfo="percent", textfont=dict(color="#e5e7eb", size=12),
    )])
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(color="#9ca3af", size=11)),
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=altura,
    )
    return fig


def grafico_evolucao_patrimonial(historico: list[dict], *, altura: int = 320, legenda: bool = True) -> go.Figure:
    """
    Patrimônio Atual x Total Investido ao longo dos snapshots — mesmo
    gráfico usado em 📊 Evolução. `legenda=False` (usado na versão
    compacta da Visão Geral) só esconde a legenda horizontal para economizar
    a pouca altura disponível ali; os dados e cores continuam os mesmos.
    """
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
        height=altura, margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color="#9ca3af")),
        xaxis=dict(color="#9ca3af", gridcolor="rgba(156,163,175,0.1)"),
        yaxis=dict(color="#9ca3af", gridcolor="rgba(156,163,175,0.1)"),
    )
    return fig
