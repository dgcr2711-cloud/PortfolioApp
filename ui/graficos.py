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

2026-09-03 (correção de bug visual, mesmo dia — Diego reportou por print de
tela que "este gráfico ficou péssimo, estava melhor antes"): duas correções
nos gráficos de linha e no donut:
  1. **Removida a `_borda_grafico()`** (o retângulo em `layout.shapes` do
     item 3 acima) — ela ficava DUPLICADA em cima da borda que o
     `st.container(border=True)` do Streamlit já desenha em toda chamada
     destes gráficos (`ui/visao_geral.py` e `ui/carteira.py`), resultando
     no "quadrado dentro de quadrado" que apareceu no print. A borda do
     container do Streamlit sozinha já é suficiente.
  2. **Range explícito no eixo Y** (`_intervalo_eixo_y`) nos dois gráficos
     de linha — sem isso, o `fill="tozeroy"` (preenchimento sutil "até o
     zero" sob a linha) combinado com um eixo Y que também autoajusta perto
     do zero fazia o preenchimento cobrir o painel inteiro, virando um
     bloco de cor sólida em vez do degradê fino pretendido (era o
     "gráfico verde péssimo" do print). Agora o eixo Y fica limitado a uma
     faixa próxima do mínimo/máximo real dos dados (com uma margem de
     respiro), então o preenchimento "até o zero" continua matematicamente
     indo até zero mas fica visualmente cortado fora da área visível.

2026-09-03 (2ª correção de bug visual, mesmo dia — novo print do Diego
mostrando uma linha ondulada/estranha embaixo do gráfico de Evolução
Patrimonial, no espaço entre a linha "Total Investido" e o eixo X):
consequência direta da correção #2 acima — como o eixo Y passou a ter um
range que NÃO inclui mais o zero (de propósito, pra cortar o preenchimento
"até o zero" fora da área visível), o preenchimento `fill="tozeroy"`
precisa ser recortado (clipped) contra essa borda inferior do eixo, e esse
recorte estava saindo ondulado/mal-desenhado na renderização — em vez de
uma borda reta. Correção: **removido o preenchimento (`fill`/`fillcolor`)
dos dois gráficos de linha por completo** — voltam a ser só a linha, sem
área sombreada embaixo.

2026-09-04 (preenchimento sob a linha, de volta — pedido do Diego, "este
gráfico a dois dias tb tinha coloração abaixo da linha, o que deixa mais
interativo"): a remoção acima resolveu o bug, mas o motivo raiz nunca foi
"ter preenchimento", foi usar `fill="tozeroy"` (que aponta pro y=0
matemático, longe da faixa visível) e depender do Plotly recortar isso
contra o range do eixo — esse recorte é que saía ondulado. A técnica nova
evita o recorte por completo: cada gráfico de linha ganha uma trace
"piso" invisível (`line=dict(width=0)`, sem hover, sem legenda) com y
constante igual ao MÍNIMO do range do eixo Y (o mesmo valor de
`_intervalo_eixo_y`) — e a trace principal usa `fill="tonexty"` contra
essa trace-piso, em vez de `"tozeroy"`. Como a trace-piso já está
exatamente na borda inferior visível do gráfico, o preenchimento nunca
precisa ser recortado (não existe área "fora" pra cortar) — sai sempre
com uma borda reta, não importa a combinação de dados/range. Aplicado só
na linha principal de cada gráfico (Patrimônio Atual / Fechamento) — a
linha de referência (Total Investido, tracejada) continua sem
preenchimento, pra não sobrepor duas áreas coloridas e poluir a leitura.

2026-09-04 (nova função, mesmo dia — pedido do Diego: "camada por setor
com um gráfico pequeno pra cada ação lado a lado"): `grafico_sparkline`,
uma versão minúscula dos gráficos de linha acima — sem eixo, sem legenda,
sem hover, só a forma da curva — pra caber várias lado a lado num card
compacto por ativo (ver `ui/visao_geral.py::_render_por_setor`). Reaproveita
a mesma técnica de trace-piso + `fill="tonexty"` de cima, mas a cor é
dinâmica por ativo (verde se subiu no período, vermelho se caiu — decidido
por quem chama), daí o helper `_hex_para_rgba` pra gerar o `fillcolor` a
partir da cor da linha em vez de uma cor fixa.
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

# Cor dos eixos/grade dos gráficos de linha — mesmo tom "texto secundário"
# usado no resto do app (ui/styles.py), pra eixo/grade ficarem discretos e
# consistentes com rótulos e legendas fora do gráfico.
_COR_EIXO = COR_TEXTO_SECUNDARIO
_COR_GRADE = "rgba(161,161,170,0.12)"


def _intervalo_eixo_y(*series: list[float], margem_pct: float = 0.08) -> list[float]:
    """
    Range explícito pro eixo Y, com uma margem de "respiro" acima/abaixo do
    mínimo/máximo real dos dados (2026-09-03, correção do bug do "gráfico
    verde sólido" reportado pelo Diego).

    Por quê: sem um range de eixo Y explícito, o Plotly autoajusta o eixo
    partindo de perto do zero — mas como os valores reais (ex.: patrimônio
    ~R$ 700 mil) estão muito longe de zero, o gráfico fica "espremido" lá
    em cima, sem aproveitar a altura disponível pra mostrar a variação de
    verdade. Dando ao eixo um range próximo do mínimo/máximo real (com uma
    margem de respiro), o gráfico usa a altura toda pra mostrar a variação.

    Desde 2026-09-04, o MÍNIMO deste range também vira o "piso" onde o
    preenchimento sob a linha principal é ancorado (`fill="tonexty"` contra
    uma trace invisível nesse valor — ver docstring do módulo) em vez do
    antigo `fill="tozeroy"`, que ia até o zero matemático e dependia do
    Plotly recortar isso contra o range visível (o recorte é que saía
    ondulado no bug reportado pelo Diego).

    Aceita várias séries de uma vez (ex.: "Patrimônio Atual" + "Total
    Investido", ou "Fechamento" + a linha de preço-teto) pra que o range
    cubra todas elas.
    """
    valores = [v for serie in series for v in serie if v is not None]
    if not valores:
        return [0, 1]
    minimo, maximo = min(valores), max(valores)
    if minimo == maximo:
        respiro = abs(minimo) * margem_pct or 1
        return [minimo - respiro, maximo + respiro]
    respiro = (maximo - minimo) * margem_pct
    # Valores financeiros aqui (patrimônio, preço de fechamento) nunca são
    # negativos — o piso em 0 evita um respiro inútil abaixo de zero.
    return [max(0, minimo - respiro), maximo + respiro]


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
    eixo_x, eixo_y = _eixos_com_crosshair()
    eixo_y["range"] = _intervalo_eixo_y(valores_atual, valores_investido)

    # Trace "piso" invisível, só para ancorar o preenchimento sob a linha
    # de Patrimônio Atual sem recorte (ver docstring do módulo, 2026-09-04)
    # — precisa vir ANTES da trace que usa fill="tonexty", que preenche
    # contra a trace imediatamente anterior.
    fig.add_trace(go.Scatter(
        x=datas, y=[eixo_y["range"][0]] * len(datas), mode="lines",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))
    # customdata leva o valor já formatado em R$ no padrão brasileiro
    # (vírgula decimal) pro hover — o formato nativo do Plotly (%{y:,.2f})
    # sairia em padrão americano (ponto decimal), inconsistente com o
    # resto do app.
    fig.add_trace(go.Scatter(
        x=datas, y=valores_atual, name="Patrimônio Atual",
        line=dict(color="#34d399", width=2),
        fill="tonexty", fillcolor="rgba(52,211,153,0.14)",
        customdata=[formatar_moeda(v) for v in valores_atual],
        hovertemplate="<b>%{customdata}</b><extra>Patrimônio Atual</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=datas, y=valores_investido, name="Total Investido",
        line=dict(color="#9ca3af", width=2, dash="dash"),
        customdata=[formatar_moeda(v) for v in valores_investido],
        hovertemplate="<b>%{customdata}</b><extra>Total Investido</extra>",
    ))
    fig.update_layout(
        height=altura, margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=_COR_EIXO)),
        hovermode="x unified",
        xaxis=eixo_x,
        yaxis=eixo_y,
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
    eixo_x, eixo_y = _eixos_com_crosshair()
    series_range = [fechamentos]
    if preco_teto_com_margem is not None:
        series_range.append([preco_teto_com_margem])
    eixo_y["range"] = _intervalo_eixo_y(*series_range)

    # Trace "piso" invisível — mesma técnica de grafico_evolucao_patrimonial
    # acima (ver docstring do módulo, 2026-09-04), pra ancorar o
    # preenchimento sob a linha de Fechamento sem recorte/artefato.
    fig.add_trace(go.Scatter(
        x=datas, y=[eixo_y["range"][0]] * len(datas), mode="lines",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=datas, y=fechamentos, name="Fechamento",
        line=dict(color=COR_LINHA_ATIVO, width=2),
        fill="tonexty", fillcolor="rgba(56,189,248,0.14)",
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
    fig.update_layout(
        height=altura, margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hovermode="x unified",
        xaxis=eixo_x,
        yaxis=eixo_y,
    )
    return fig


def grafico_sparkline(pontos: list[dict], *, cor: str, altura: int = 56) -> go.Figure:
    """
    Mini-gráfico de tendência ("sparkline") — sem eixos, sem legenda, sem
    hover, só a forma da linha (pedido do Diego, 2026-09-04: "camada por
    setor com um gráfico pequeno pra cada ação lado a lado"). Usado só nos
    cards compactos de `ui/visao_geral.py::_card_sparkline_ativo`, dentro
    do expander "🏭 Por Setor" — um "glance" bem menor que
    `grafico_preco_individual` (que continua sendo o lugar pra olhar um
    ativo com detalhe, crosshair e preço-teto, na aba Carteira).

    `cor`: hexadecimal (ex.: "#34d399") — quem chama decide (verde/vermelho
    conforme a variação do período, ver `_card_sparkline_ativo`), pra ficar
    óbvio de relance se a ação subiu ou caiu no período sem precisar ler
    nenhum número.

    Reaproveita a técnica da trace-piso + `fill="tonexty"` (ver docstring
    do módulo) pro mesmo preenchimento sutil sob a linha dos outros
    gráficos daqui — o range do eixo Y ainda existe internamente
    (`_intervalo_eixo_y`, com mais respiro que o padrão porque não há
    grade/rótulo pra "ancorar" visualmente a curva), só não é desenhado.
    """
    fig = go.Figure()
    fechamentos = [p["fechamento"] for p in pontos]
    eixo_y_range = _intervalo_eixo_y(fechamentos, margem_pct=0.12)

    # Trace "piso" invisível — mesma técnica dos gráficos de linha acima.
    fig.add_trace(go.Scatter(
        y=[eixo_y_range[0]] * len(fechamentos), mode="lines",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        y=fechamentos, mode="lines",
        line=dict(color=cor, width=1.6),
        fill="tonexty", fillcolor=_hex_para_rgba(cor, 0.16),
        hoverinfo="skip", showlegend=False,
    ))
    fig.update_layout(
        height=altura, margin=dict(t=2, b=2, l=2, r=2),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, range=eixo_y_range, fixedrange=True),
    )
    return fig


def _hex_para_rgba(hex_cor: str, alpha: float) -> str:
    """
    Converte "#RRGGBB" em "rgba(r,g,b,alpha)" — usado só pelo preenchimento
    do `grafico_sparkline` acima, cuja cor varia por ativo (verde/vermelho
    conforme a tendência do período); os outros gráficos deste módulo têm
    cor fixa, então já escrevem o `rgba(...)` direto sem precisar converter.
    """
    hex_cor = hex_cor.lstrip("#")
    r, g, b = int(hex_cor[0:2], 16), int(hex_cor[2:4], 16), int(hex_cor[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
