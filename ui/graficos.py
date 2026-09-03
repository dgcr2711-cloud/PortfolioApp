"""
Gráficos (plotly) compartilhados entre abas — extraído em 2026-09-03 para
que a Visão Geral pudesse ganhar os mesmos gráficos de Alocação (antes só
em 📈 Carteira) e Evolução Patrimonial (antes só em 📊 Evolução) sem
duplicar a definição de cores/estilo em três lugares. `ui/carteira.py` e
`ui/evolucao.py` foram atualizados para importar daqui.

2026-09-03 (refinamento estético, mesma data): dois ajustes a pedido do
Diego, no espírito "estética minimalista, um gráfico por vez" —
  1. `grafico_alocacao` passou a rotular cada fatia com "TICKER - XX,X%"
     direto no gráfico (sem legenda separada, que ficava redundante e
     ocupava espaço à toa).
  2. Nova `grafico_preco_individual`: gráfico de UM ativo por vez (linha
     de fechamento + preço-teto de referência), usado em 📈 Carteira no
     lugar do donut de alocação — que passou a viver só na Visão Geral
     (ver `ui/graficos.py`'s comentário em `grafico_alocacao` e
     `ui/carteira.py::_secao_grafico_individual`).
"""

from __future__ import annotations

import plotly.graph_objects as go

from core.formatting import formatar_data_br

PALETA_ALOCACAO = ["#34d399", "#38bdf8", "#fbbf24", "#a78bfa", "#F87171", "#22d3ee", "#f472b6", "#a3e635", "#fb923c", "#94a3b8"]

COR_LINHA_ATIVO = "#38bdf8"
COR_PRECO_TETO = "#fbbf24"


def grafico_alocacao(labels: list[str], valores: list[float], *, altura: int = 320) -> go.Figure:
    """
    Donut de alocação (por ativo ou por setor) — usado hoje só na Visão
    Geral (2026-09-03: removido de 📈 Carteira para não duplicar o mesmo
    gráfico em duas telas — lá, o espaço virou o gráfico individual por
    ativo, ver `grafico_preco_individual`).

    Cada fatia mostra "RÓTULO - XX,X%" (pedido do Diego, ex: "PETR4 -
    15,4%") com uma linha guia pra fora da rosca — igual ao efeito visual
    de apps como o TradeMap — em vez de uma legenda separada ao lado, que
    ficava redundante (o rótulo já diz tudo) e roubava espaço horizontal
    do gráfico em telas menores.
    """
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=valores, hole=0.55,
        marker=dict(colors=PALETA_ALOCACAO, line=dict(color="#111827", width=2)),
        texttemplate="%{label} - %{percent}",
        textposition="outside",
        textfont=dict(color="#e5e7eb", size=12),
    )])
    fig.update_layout(
        showlegend=False,
        margin=dict(t=40, b=40, l=70, r=70),
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


def grafico_preco_individual(
    pontos: list[dict], *, preco_teto_com_margem: float | None = None, altura: int = 340,
) -> go.Figure:
    """
    Gráfico "de um ativo só" (pedido do Diego, 2026-09-03): substitui, na
    aba Carteira, o gráfico consolidado de vários ativos/setores ao mesmo
    tempo — a ideia é reduzir quanta informação aparece simultaneamente na
    tela, deixando o usuário escolher QUAL ativo quer olhar de cada vez
    (ver `ui/carteira.py::_secao_grafico_individual`).

    `pontos`: lista de {"data": "AAAA-MM-DD", "fechamento": float}, na
    ordem cronológica — formato devolvido por
    `core.market_data.buscar_historico_preco`.

    Quando `preco_teto_com_margem` é informado, desenha uma linha
    horizontal tracejada de referência (o "preço bom pra comprar" já com a
    margem de segurança descontada — mesmo número mostrado na tabela de
    posições) — útil pra ver de relance se o preço atual está acima ou
    abaixo dele, sem precisar abrir outra aba.
    """
    fig = go.Figure()
    datas = [formatar_data_br(p["data"]) for p in pontos]
    fechamentos = [p["fechamento"] for p in pontos]
    fig.add_trace(go.Scatter(
        x=datas, y=fechamentos, name="Fechamento",
        line=dict(color=COR_LINHA_ATIVO, width=2), fill="tozeroy", fillcolor="rgba(56,189,248,0.08)",
    ))
    if preco_teto_com_margem is not None:
        fig.add_hline(
            y=preco_teto_com_margem,
            line=dict(color=COR_PRECO_TETO, width=1.5, dash="dash"),
            annotation_text="Preço Teto c/ Margem",
            annotation_position="top left",
            annotation_font=dict(color=COR_PRECO_TETO, size=11),
        )
    fig.update_layout(
        height=altura, margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(color="#9ca3af", gridcolor="rgba(156,163,175,0.1)"),
        yaxis=dict(color="#9ca3af", gridcolor="rgba(156,163,175,0.1)"),
    )
    return fig
