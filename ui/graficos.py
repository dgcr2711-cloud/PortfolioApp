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

2026-09-03 (refinamento visual, mesmo dia, pedido do Diego — "gráfico
mais bonito, cores diferentes, com borda"): os 3 gráficos daqui ganharam
uma moldura fina desenhada no próprio Plotly (`_borda_grafico()` — um
retângulo em `layout.shapes`, não depende de nenhum container do
Streamlit, então funciona igual em qualquer lugar que o gráfico apareça).
`grafico_alocacao` ganhou uma paleta nova, mais variada, e passou a
aceitar um total opcional no centro da rosca (`valor_central`/
`rotulo_central` — mesmo padrão do donut do celular,
`GraficoDonutAlocacao.tsx`). Os dois parâmetros já vêm PRÉ-FORMATADOS de
quem chama (`ui/visao_geral.py`, via `formatar_moeda_priv`) de propósito:
este módulo não sabe nada sobre "ocultar valores", quem chama decide como
mascarar — mesmo motivo pelo qual `texttemplate`/`hovertemplate` abaixo
nunca mostram um valor em R$, só rótulo e percentual (o hover funciona
igual não importa o modo de privacidade).

2026-09-03 (3º refinamento visual do dia, pedido do Diego — "deixar os
gráficos mais bonitos/estruturados, pesquisar sites próprios pra ideias"):
pesquisei o skill interno de dataviz da Anthropic (metodologia de cor/
forma/interação, independente de produto) e artigos reais sobre design de
dashboard de investimentos (ver a resposta no chat pros links) antes de
mexer em qualquer coisa. Mudanças que vieram direto dessa pesquisa:
  1. **Paleta do donut re-validada** — a paleta anterior falhava o
     validador de acessibilidade do skill (`scripts/validate_palette.js`)
     em 3 dos 5 testes (banda de luminosidade, piso de saturação,
     separação para daltonismo). A nova (7 cores, ver PALETA_ALOCACAO)
     passa os 5 testes rodando contra o fundo real do app (#252324) —
     ela é uma ordem validada de um palette de referência, com a fatia
     vermelha removida de propósito (mesmo motivo de antes: essa cor já
     significa prejuízo/queda no resto do app).
  2. **Fatias do donut mostram R$ + % juntos** (não só %) quando os
     valores não estão ocultos — vários artigos de UX de dashboard
     financeiro batem nisso: "não obrigue o usuário a inferir o valor a
     partir só do percentual". Continua caindo pra "só %" no modo
     "ocultar valores" (nenhuma mudança na privacidade).
  3. **Crosshair no hover dos gráficos de linha** (Evolução Patrimonial e
     Gráfico do Ativo) — `hovermode="x unified"` + linha-guia
     (`showspikes`), pra ver o valor exato em qualquer ponto sem precisar
     "estimar visualmente" (padrão comum em produtos financeiros de
     verdade — Kinvo, StatusInvest, TradeMap etc. todos têm isso).
  4. Borda dos gráficos ajustada pra um "anel" bem mais sutil (linha fina
     translúcida, no espírito do "hairline ring" que o skill de dataviz
     recomenda pra modo escuro) em vez da linha sólida mais grossa de
     antes.
"""

from __future__ import annotations

import plotly.graph_objects as go

from core.config import COR_FUNDO_APP, COR_TEXTO_PRIMARIO, COR_TEXTO_SECUNDARIO
from core.formatting import formatar_data_br, formatar_moeda

# Paleta "Executivo Black" (2026-09-03) — 7 cores, na ordem validada pelo
# script `validate_palette.js` do skill interno de dataviz (banda de
# luminosidade, piso de saturação, separação simulando daltonismo,
# contraste — os 5 testes passam rodando contra o fundo real do app,
# #252324). A fatia vermelha do palette de referência foi removida de
# propósito: essa cor já significa prejuízo/queda no resto do app, então
# usá-la também numa fatia do donut confundiria a leitura. Com mais de 7
# posições simultâneas, quem chama deve agrupar o excedente em "Outros"
# (ver `ui/visao_geral.py::_render_graficos_resumo`) em vez de reciclar
# cores — uma 8ª cor "inventada" não seria mais uma ordem validada.
PALETA_ALOCACAO = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9"]

COR_LINHA_ATIVO = "#38bdf8"
COR_PRECO_TETO = "#fbbf24"

# "Anel" bem sutil ao redor dos gráficos (2026-09-03, 2ª versão — linha
# fina translúcida em vez da cor sólida de antes), no espírito do
# "hairline ring" que o skill de dataviz recomenda como moldura de cartão
# em modo escuro.
_COR_BORDA_GRAFICO = "rgba(255,255,255,0.12)"

# Cor dos eixos/grade dos gráficos de linha — mesmo tom "texto secundário"
# usado no resto do app (ui/styles.py), pra eixo/grade ficarem discretos e
# consistentes com rótulos e legendas fora do gráfico.
_COR_EIXO = COR_TEXTO_SECUNDARIO
_COR_GRADE = "rgba(161,161,170,0.12)"


def _borda_grafico() -> dict:
    """
    Retângulo fino ao redor do gráfico inteiro (canto a canto do "papel"
    do Plotly) — a forma de dar um "borda" a um gráfico Plotly sem
    depender do container do Streamlit (que só tem uma borda genérica,
    igual em todo o app, e nem sempre está presente onde o gráfico é
    usado). Reaproveitado pelos 3 gráficos deste módulo.
    """
    return dict(
        type="rect", xref="paper", yref="paper", x0=0, y0=0, x1=1, y1=1,
        line=dict(color=_COR_BORDA_GRAFICO, width=1), fillcolor="rgba(0,0,0,0)",
    )


def _eixos_com_crosshair() -> tuple[dict, dict]:
    """
    Eixo X com "spike" (linha-guia vertical que acompanha o cursor,
    2026-09-03 — pesquisa de referências de dashboards financeiros reais):
    junto com `hovermode="x unified"`, mostra o valor exato de cada série
    naquele ponto sem o usuário precisar estimar visualmente na régua do
    gráfico. Reaproveitado pelos 2 gráficos de linha deste módulo.
    """
    eixo_x = dict(
        color=_COR_EIXO, gridcolor=_COR_GRADE,
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikecolor="rgba(255,255,255,0.25)", spikethickness=1, spikedash="solid",
    )
    eixo_y = dict(color=_COR_EIXO, gridcolor=_COR_GRADE)
    return eixo_x, eixo_y


def grafico_alocacao(
    labels: list[str], valores: list[float], *, altura: int = 320,
    valor_central: str | None = None, rotulo_central: str | None = None,
    valores_formatados: list[str] | None = None,
) -> go.Figure:
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

    `valor_central`/`rotulo_central` (opcionais): texto já formatado pra
    aparecer no meio da rosca (ex: valor_central="R$ 12.345,67",
    rotulo_central="Patrimônio") — mesma ideia do centro do donut do
    celular. Omitidos, o centro fica vazio (comportamento de antes).

    `valores_formatados` (opcional, 2026-09-03 — pesquisa de dashboards de
    investimento reais): um R$ já formatado por fatia, na mesma ordem de
    `labels` (ex: ["R$ 3.500,00", "R$ 2.900,00"]) — cada fatia passa a
    mostrar "TICKER - R$ X,XX - XX,X%" em vez de só "TICKER - XX,X%".
    Omitido (ou None), o comportamento é o de antes (só rótulo + %) — é
    assim que `ui/visao_geral.py` chama esta função no modo "ocultar
    valores", já que aqui dentro não se sabe nada sobre privacidade.
    """
    if valores_formatados:
        texto_fatia = [f"{rotulo} - {valor}" for rotulo, valor in zip(labels, valores_formatados)]
        texttemplate = "%{text} - %{percent}"
        hovertemplate = "<b>%{text}</b> - %{percent}<extra></extra>"
    else:
        texto_fatia = None
        texttemplate = "%{label} - %{percent}"
        hovertemplate = "<b>%{label}</b><br>%{percent}<extra></extra>"

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=valores, hole=0.6,
        marker=dict(colors=PALETA_ALOCACAO, line=dict(color=COR_FUNDO_APP, width=2)),
        text=texto_fatia,
        texttemplate=texttemplate,
        textposition="outside",
        textfont=dict(color="#e5e7eb", size=12),
        pull=[0.015] * len(labels),
        hovertemplate=hovertemplate,
    )])
    anotacoes = []
    if valor_central:
        anotacoes.append(dict(
            text=f"<b>{valor_central}</b>", x=0.5, y=0.54, xanchor="center", showarrow=False,
            font=dict(size=16, color=COR_TEXTO_PRIMARIO),
        ))
    if rotulo_central:
        anotacoes.append(dict(
            text=rotulo_central, x=0.5, y=0.43, xanchor="center", showarrow=False,
            font=dict(size=11, color=COR_TEXTO_SECUNDARIO),
        ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=40, b=40, l=70, r=70),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=altura,
        annotations=anotacoes,
        shapes=[_borda_grafico()],
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
    valores_atual = [h["totalAtual"] for h in historico]
    valores_investido = [h["totalInvestido"] for h in historico]
    # customdata leva o valor já formatado em R$ no padrão brasileiro
    # (vírgula decimal) pro hover — o formato nativo do Plotly (%{y:,.2f})
    # sairia em padrão americano (ponto decimal), inconsistente com o
    # resto do app.
    fig.add_trace(go.Scatter(
        x=datas, y=valores_atual, name="Patrimônio Atual",
        line=dict(color="#34d399", width=2), fill="tozeroy", fillcolor="rgba(52,211,153,0.1)",
        customdata=[formatar_moeda(v) for v in valores_atual],
        hovertemplate="<b>%{customdata}</b><extra>Patrimônio Atual</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=datas, y=valores_investido, name="Total Investido",
        line=dict(color="#9ca3af", width=2, dash="dash"),
        customdata=[formatar_moeda(v) for v in valores_investido],
        hovertemplate="<b>%{customdata}</b><extra>Total Investido</extra>",
    ))
    eixo_x, eixo_y = _eixos_com_crosshair()
    fig.update_layout(
        height=altura, margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=_COR_EIXO)),
        hovermode="x unified",
        xaxis=eixo_x,
        yaxis=eixo_y,
        shapes=[_borda_grafico()],
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
        customdata=[formatar_moeda(v) for v in fechamentos],
        hovertemplate="<b>%{customdata}</b><extra>Fechamento</extra>",
    ))
    if preco_teto_com_margem is not None:
        fig.add_hline(
            y=preco_teto_com_margem,
            line=dict(color=COR_PRECO_TETO, width=1.5, dash="dash"),
            annotation_text="Preço Teto c/ Margem",
            annotation_position="top left",
            annotation_font=dict(color=COR_PRECO_TETO, size=11),
        )
    eixo_x, eixo_y = _eixos_com_crosshair()
    fig.update_layout(
        height=altura, margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hovermode="x unified",
        xaxis=eixo_x,
        yaxis=eixo_y,
        shapes=[_borda_grafico()],
    )
    return fig
