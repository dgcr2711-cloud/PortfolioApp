"""
CSS e pequenos componentes visuais reutilizados em várias abas, para que
os cards de resumo e os badges (🟢 Compra / 🟡 Neutro / 🔴 Venda etc.) fiquem
com a mesma cara do dashboard HTML original — mesmas cores, mesmo formato
de "pílula" arredondada.

O tema escuro geral (fundo, cor de destaque) vem do arquivo
`.streamlit/config.toml`, que é a forma oficial e estável de temizar um
app Streamlit. Aqui só completamos os detalhes que o tema não cobre.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from core.config import (
    COR_DESTAQUE,
    COR_FUNDO_CARD,
    COR_INFO,
    COR_NEGATIVO,
    COR_NEUTRO,
    COR_POSITIVO,
    COR_TEXTO_PRIMARIO,
    COR_TEXTO_SECUNDARIO,
)

CSS_GLOBAL = f"""
<style>
/* Aproveitamento de espaço (2026-09-03, pedido do Diego: "otimização" dos
   espaços vazios, tudo cabendo melhor numa tela de notebook). O Streamlit
   por padrão reserva bastante respiro no topo da página e entre cada
   bloco (título, gráfico, tabela...) — pensado pra apps genéricos, não pra
   um dashboard denso como este. As regras abaixo comprimem esse respiro
   SEM mudar a largura útil (layout="wide" continua controlando isso em
   app.py) — só a altura ocupada por espaço vazio diminui. */
.block-container {{
    padding-top: 2rem !important;
    padding-bottom: 2.5rem !important;
}}
div[data-testid="stVerticalBlock"] {{ gap: 0.6rem; }}
h1 {{ font-size: 1.65rem !important; margin: 0 0 0.15rem 0 !important; padding-top: 0 !important; }}
h2 {{ font-size: 1.25rem !important; margin: 0.3rem 0 0.2rem 0 !important; }}
h3 {{ font-size: 1.1rem !important; margin: 0.3rem 0 0.2rem 0 !important; }}
div[data-testid="stCaptionContainer"] {{ margin-bottom: 0.1rem !important; }}

/* Cards de resumo (KPIs) — mesmo visual do dashboard original, com um
   acabamento "institucional": borda sutil em degradê, leve sombra e uma
   barra superior fina que assume a cor do indicador quando informada
   (COR_DESTAQUE nas leituras mais importantes para o value investing). */
.grid-cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1rem;
}}
.card-kpi {{
    background: linear-gradient(180deg, {COR_FUNDO_CARD} 0%, #182230 100%);
    border: 1px solid #313d4f;
    border-radius: 0.85rem;
    padding: 0.8rem 1.1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.25);
    position: relative;
    overflow: hidden;
}}
.card-kpi.destaque {{ border-color: rgba(212,175,55,0.45); }}
.card-kpi.destaque::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: {COR_DESTAQUE};
}}
.card-kpi .rotulo {{
    font-size: 11px; font-weight: 600; color: {COR_TEXTO_SECUNDARIO};
    text-transform: uppercase; letter-spacing: 0.05em;
}}
.card-kpi .valor {{
    font-size: 1.25rem; font-weight: 700; color: {COR_TEXTO_PRIMARIO}; margin-top: 0.2rem;
    font-variant-numeric: tabular-nums;
}}
.card-kpi .subvalor {{ font-size: 12px; font-weight: 500; margin-top: 0.1rem; }}

/* Cards "primário" (KPIs essenciais, valor grande) vs "compacto"
   (secundários — contagens, alertas) — 2026-09-03, pedido do Diego:
   divulgação progressiva também dentro da própria linha de KPIs da Visão
   Geral, não só nos expanders. Os 2-3 números que mais importam
   (Patrimônio, Resultado, Proventos) continuam do tamanho normal; o resto
   fica visível mas discreto, numa segunda linha menor, sem competir em
   destaque visual com o que importa mais. */
.card-kpi.compacto {{ padding: 0.55rem 0.9rem; }}
.card-kpi.compacto .rotulo {{ font-size: 10px; }}
.card-kpi.compacto .valor {{ font-size: 1.0rem; margin-top: 0.1rem; }}

/* Realce interativo em TODOS os cards (2026-09-04, pedido do Diego —
   "criar alguma borda interativa ou com cores realçadas em todos os
   cards, fica legal a visualização e valoriza o projeto"): ao passar o
   mouse, a borda do card assume a cor de destaque dourada (mesma
   COR_DESTAQUE usada no resto do app — nenhuma cor nova entra no tema) e
   ganha um leve brilho + "levantada" de 1px, com transição suave. Cobre
   tanto os cards HTML manuais (.card-kpi e os outros cards deste arquivo)
   quanto os containers nativos do Streamlit com borda
   (`st.container(border=True)` — usados nos cards de gráfico da Visão
   Geral/Carteira), pra ficar consistente em toda a tela, não só nos
   cards "manuais". `transform: translateY(-1px)` é sutil de propósito —
   o objetivo é indicar "isto é interativo", não distrair. */
.card-kpi,
.card-tabela,
.painel-diagnostico,
.card-proximos-proventos,
.cal-dia,
div[data-testid="stVerticalBlockBorderWrapper"] {{
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}}
.card-kpi:hover,
.card-tabela:hover,
.painel-diagnostico:hover,
.card-proximos-proventos:hover,
.cal-dia:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    border-color: rgba(212,175,55,0.55) !important;
    box-shadow: 0 0 0 1px rgba(212,175,55,0.18), 0 6px 16px rgba(0,0,0,0.35);
    transform: translateY(-1px);
}}
/* Card já em destaque (borda dourada permanente) fica só um pouco mais
   forte no hover, pra não parecer que "perdeu" o destaque que já tinha. */
.card-kpi.destaque:hover {{ border-color: rgba(212,175,55,0.85) !important; }}

/* Aviso de privacidade (LGPD/"ocultar valores") — substitui o gráfico de
   Evolução Patrimonial quando o modo de ocultar valores está ativo
   (2026-09-03, pedido do Diego): a série histórica em R$ some da tela por
   completo (não só mascarada com ••••, que ainda revelaria a FORMA da
   curva) — fica claro que a informação está intencionalmente escondida,
   não que faltam dados. O donut de Alocação não precisa desse tratamento:
   ele já mostra só Ticker + percentual, nunca um valor em R$. */
.aviso-privacidade {{
    background: {COR_FUNDO_CARD}; border: 1px dashed #3a3a3c; border-radius: 0.85rem;
    padding: 1.4rem 1rem; text-align: center; color: {COR_TEXTO_SECUNDARIO};
    font-size: 13px;
}}
.aviso-privacidade .icone {{ font-size: 1.4rem; margin-bottom: 0.3rem; display: block; }}

/* Badges (pílulas coloridas) — mesmas classes/cores do HTML original */
.badge {{
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 11px; font-weight: 600; padding: 2px 8px;
    border-radius: 9999px; white-space: nowrap;
}}
.badge-ok {{ background: rgba(16,185,129,0.15); color: {COR_POSITIVO}; border: 1px solid rgba(16,185,129,0.4); }}
.badge-warn {{ background: rgba(244,63,94,0.15); color: {COR_NEGATIVO}; border: 1px solid rgba(244,63,94,0.4); }}
.badge-neutral {{ background: rgba(156,163,175,0.12); color: {COR_NEUTRO}; border: 1px solid rgba(156,163,175,0.3); }}
.badge-info {{ background: rgba(56,189,248,0.15); color: {COR_INFO}; border: 1px solid rgba(56,189,248,0.4); }}
.badge-destaque {{ background: rgba(212,175,55,0.14); color: {COR_DESTAQUE}; border: 1px solid rgba(212,175,55,0.4); }}
.texto-apagado {{ color: #6b7280; font-size: 12px; }}

/* Linha de badges lado a lado (ex: resumo "Por tipo" da aba Proventos) —
   substitui o que antes eram vários st.metric grandes por pílulas
   pequenas, mais compactas e sem competir em destaque com os KPIs. */
.linha-badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0.15rem 0 1.15rem 0; }}

/* Moldura que envolve as tabelas HTML "manuais" (Visão Geral / Carteira /
   Fundamentos) — 2026-09-02: antes elas ficavam soltas direto no fundo
   escuro da página, sem nenhuma borda, destoando dos cards de KPI e do
   Painel de Diagnóstico (que sempre tiveram essa moldura). Agora toda
   tabela grande vive dentro do mesmo "cartão" institucional usado no
   resto do app. */
.card-tabela {{
    background: {COR_FUNDO_CARD}; border: 1px solid #313d4f; border-radius: 0.85rem;
    padding: 0.35rem 0.85rem; box-shadow: 0 1px 2px rgba(0,0,0,0.25);
    overflow-x: auto; margin-bottom: 0.75rem;
}}
.card-tabela table {{ margin: 0; }}

/* Tabela "manual" (Visão Geral / Carteira / Fundamentos) para reproduzir
   exatamente o mesmo layout de colunas do dashboard original. */
table.tabela-carteira {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.tabela-carteira th {{
    text-align: left; padding: 8px; color: #9ca3af; font-size: 11px;
    text-transform: uppercase; border-bottom: 1px solid #374151; font-weight: 600;
}}
table.tabela-carteira td {{ padding: 8px; border-bottom: 1px solid #27303f; vertical-align: middle; }}
table.tabela-carteira tr:hover {{ background: rgba(255,255,255,0.02); }}
table.tabela-carteira tr.linha-alvo {{ border-left: 3px solid {COR_INFO}; }}
table.tabela-carteira .ticker {{ font-weight: 700; color: {COR_TEXTO_PRIMARIO}; }}
table.tabela-carteira .setor {{ font-size: 11px; color: {COR_TEXTO_SECUNDARIO}; }}
/* Segunda linha, menor, dentro de uma célula que junta duas informações
   relacionadas na mesma coluna (ex: Cotação + Variação do Dia, ou Preço
   Teto + margem de segurança) — 2026-09-02, reduz o nº de colunas da
   tabela de Posições pra sofrer menos com rolagem lateral em notebooks. */
table.tabela-carteira .subcelula {{ font-size: 11px; color: #9ca3af; margin-top: 3px; }}

/* Painel de diagnóstico institucional (Visão Geral) — bloco com destaque
   visual próprio, separado dos cards de KPI comuns. */
.painel-diagnostico {{
    background: linear-gradient(135deg, #1a2233 0%, #161d2b 100%);
    border: 1px solid rgba(212,175,55,0.25);
    border-radius: 0.85rem;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.75rem;
}}
.painel-diagnostico h4 {{
    margin: 0 0 0.45rem 0 !important; font-size: 13px; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; color: {COR_DESTAQUE};
}}
.linha-diagnostico {{
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 0.28rem 0; border-bottom: 1px dashed rgba(255,255,255,0.06);
    font-size: 13px;
}}
.linha-diagnostico:last-child {{ border-bottom: none; }}
.linha-diagnostico .rotulo-diag {{ color: #c3cad6; }}
.linha-diagnostico .valor-diag {{ font-weight: 700; color: {COR_TEXTO_PRIMARIO}; text-align: right; }}
.selo-fonte {{
    display: inline-block; font-size: 10px; color: #6b7280; margin-top: 0.5rem;
    letter-spacing: 0.02em;
}}

/* "Mapa de Dividendos" (aba Proventos) — grade de Ticker x Mês agrupada por
   setor, no estilo dos mapas de calor de dividendo (linhas = ativos,
   colunas = Jan..Dez, célula destacada = mês em que o ativo historicamente
   pagou). A opacidade da célula vem de quantas vezes esse mês já se repetiu
   no histórico do usuário (mais repetições = mais destaque). */
table.mapa-dividendos {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
table.mapa-dividendos th {{
    text-align: center; padding: 6px 3px; color: #9ca3af; font-size: 10px;
    text-transform: uppercase; border-bottom: 1px solid #374151; font-weight: 600;
}}
table.mapa-dividendos th.col-ticker {{ text-align: left; padding-left: 8px; }}
table.mapa-dividendos td {{
    padding: 5px 3px; border-bottom: 1px solid #202836; text-align: center; vertical-align: middle;
}}
table.mapa-dividendos td.col-ticker {{
    text-align: left; padding-left: 8px; font-weight: 700; color: #ffffff; white-space: nowrap;
}}
table.mapa-dividendos tr.linha-setor td {{
    background: rgba(255,255,255,0.04); font-weight: 700; color: {COR_DESTAQUE};
    text-transform: uppercase; font-size: 10px; letter-spacing: 0.06em;
    padding: 8px 3px 6px 8px; text-align: left; border-bottom: 1px solid #374151;
}}
table.mapa-dividendos .mes-pago {{ border-radius: 5px; color: {COR_POSITIVO}; font-weight: 700; }}
table.mapa-dividendos .mes-anunciado {{
    border-radius: 5px; color: {COR_INFO}; font-weight: 700; border: 1px dashed rgba(56,189,248,0.55);
}}
table.mapa-dividendos .mes-vazio {{ color: #2b3544; }}
table.mapa-dividendos tr.linha-so-automatica td.col-ticker {{ color: {COR_INFO}; }}

/* Cards de "Próximos Dividendos" (aba Proventos) — layout inspirado no
   app "Agenda Dividendos" que o usuário mostrou como referência: um card
   arredondado por grupo (Carteira / Watchlist), cabeçalho colorido,
   tabela compacta e uma linha de total somado no rodapé. Mantido no
   MESMO tema escuro do resto do app (não a paleta clara/verde-água do
   app de referência), pra não destoar visualmente das outras abas. */
.card-proximos-proventos {{
    background: {COR_FUNDO_CARD}; border: 1px solid #313d4f; border-radius: 0.85rem;
    overflow: hidden; margin-bottom: 1.25rem; box-shadow: 0 1px 2px rgba(0,0,0,0.25);
}}
.card-proximos-proventos .cabecalho-grupo {{
    background: linear-gradient(90deg, {COR_POSITIVO} 0%, #0f9c73 100%);
    color: #06231a; font-weight: 700; padding: 0.6rem 1rem; font-size: 0.95rem;
}}
table.tabela-proximos-proventos {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.tabela-proximos-proventos th {{
    text-align: right; padding: 8px 12px; color: #9ca3af; font-size: 10.5px;
    text-transform: uppercase; border-bottom: 1px solid #374151; font-weight: 600;
}}
table.tabela-proximos-proventos th.col-esquerda {{ text-align: left; }}
table.tabela-proximos-proventos td {{
    padding: 7px 12px; border-bottom: 1px solid #202836; text-align: right; color: #e5e7eb;
}}
table.tabela-proximos-proventos td.col-esquerda {{ text-align: left; }}
table.tabela-proximos-proventos td.col-ticker {{ font-weight: 700; color: #ffffff; }}
table.tabela-proximos-proventos td.col-total {{ font-weight: 700; color: {COR_POSITIVO}; }}
table.tabela-proximos-proventos td.col-total.sem-direito {{
    font-weight: 500; color: {COR_NEGATIVO}; font-size: 12px; font-style: italic;
}}
.card-proximos-proventos .rodape-total {{
    display: flex; justify-content: space-between; padding: 0.6rem 1rem;
    background: rgba(255,255,255,0.03); font-size: 0.85rem; color: #9ca3af;
}}
.card-proximos-proventos .rodape-total strong {{ color: {COR_POSITIVO}; font-size: 0.95rem; }}

/* "Agenda de Dividendos" (aba Proventos) — vista em calendário semanal,
   2026-09-02, no estilo do app "Agenda Dividendos" que Diego mostrou como
   referência: dias úteis lado a lado, um cartãozinho por evento (Data Com
   ou Pagamento). A pílula do ticker reaproveita as classes .badge-destaque
   (Data Com — dourado) / .badge-ok (Pagamento — verde) já usadas no resto
   do app, então nenhuma cor nova entra no tema. */
.calendario-proventos {{ display: flex; gap: 0.75rem; overflow-x: auto; padding-bottom: 0.35rem; margin-bottom: 0.5rem; }}
.cal-dia {{
    flex: 1 1 0; min-width: 160px; background: {COR_FUNDO_CARD}; border: 1px solid #313d4f;
    border-radius: 0.85rem; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.25);
}}
.cal-dia.cal-hoje {{ border-color: {COR_INFO}; }}
.cal-dia .cal-cabecalho {{ padding: 0.6rem 0.75rem 0.4rem; border-bottom: 1px solid #262f3d; }}
.cal-dia.cal-hoje .cal-cabecalho {{ border-top: 3px solid {COR_INFO}; padding-top: calc(0.6rem - 3px); }}
.cal-dia .dia-semana {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #9ca3af; }}
.cal-dia.cal-hoje .dia-semana {{ color: {COR_INFO}; }}
.cal-dia .dia-data {{ font-size: 11px; color: #6b7280; margin-top: 0.1rem; }}
.cal-dia .cal-eventos {{ padding: 0.6rem; display: flex; flex-direction: column; gap: 0.5rem; }}
.cal-evento {{ background: rgba(255,255,255,0.03); border-radius: 0.6rem; padding: 0.5rem 0.6rem; }}
.cal-evento .cal-topo {{ display: flex; justify-content: space-between; align-items: center; gap: 0.4rem; }}
.cal-evento .cal-valor {{ font-size: 12px; font-weight: 700; color: #e5e7eb; white-space: nowrap; }}
.cal-evento .cal-rotulo {{ font-size: 10.5px; color: #9ca3af; margin-top: 0.35rem; }}
</style>
"""


def injetar_css() -> None:
    """Chamado uma vez, no início do app.py."""
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)


def desativar_traducao_automatica() -> None:
    """
    Chamado uma vez, no início do app.py — pede pro navegador (Google
    Tradutor embutido no Chrome, por exemplo) NÃO oferecer/aplicar
    tradução automática nesta página.

    Por quê: o app já é todo em português, mas usa alguns termos técnicos
    de mercado financeiro deliberadamente em inglês (Payout, ROE, FCF,
    WACC, Beta, DARF etc. — são os nomes que qualquer investidor reconhece,
    mesmo no Brasil). Isso às vezes faz o Chrome desconfiar que a página
    "não está totalmente em português" e sugerir traduzi-la. Se isso
    acontecer (de propósito ou sem querer), o resultado fica PIOR, não
    melhor — é uma tradução de português pra português, e sai texto sem
    sentido (ex: "Indicadores por Ativo" virando "Praias por Ativo",
    "Payout (12m calc.)" virando "Pagamento (Cálculo de 12 Milhões)").

    A forma padrão de pedir isso a um navegador é a tag
    `<meta name="google" content="notranslate">` e o atributo
    `translate="no"` no `<html>` da página. O Streamlit não deixa editar o
    <head> diretamente, então usamos um componente (que roda num iframe do
    MESMO site) pra alcançar o documento principal via `window.parent` e
    aplicar isso lá — só precisa rodar uma vez, no carregamento da página.
    """
    components.html(
        """
        <script>
        try {
            var doc = window.parent.document;
            doc.documentElement.setAttribute('translate', 'no');
            doc.documentElement.classList.add('notranslate');
            if (!doc.querySelector('meta[name="google"]')) {
                var meta = doc.createElement('meta');
                meta.name = 'google';
                meta.content = 'notranslate';
                doc.head.appendChild(meta);
            }
        } catch (e) {}
        </script>
        """,
        height=0,
    )


def badge_html(texto: str, tipo: str) -> str:
    """tipo: 'ok' | 'warn' | 'neutral' | 'info'."""
    return f'<span class="badge badge-{tipo}">{texto}</span>'


def badge_indicacao(indicacao: str | None, motivo_ausencia: str | None = None) -> str:
    """
    Constrói o badge da coluna "Indicação" a partir do resultado de
    core.calculations.indicacao(). `motivo_ausencia` diferencia "sem preço
    teto calculado" de "sem cotação buscada ainda", igual ao original.
    """
    if indicacao is None:
        texto = motivo_ausencia or "— sem dados"
        return f'<span class="texto-apagado">{texto}</span>'
    mapa = {
        "compra": ("🟢 Compra", "ok"),
        "neutro": ("🟡 Neutro", "neutral"),
        "venda": ("🔴 Venda", "warn"),
    }
    texto, tipo = mapa[indicacao]
    return badge_html(texto, tipo)


def badge_variacao_dia(variacao_pct: float | None) -> str:
    if variacao_pct is None:
        return '<span class="texto-apagado">—</span>'
    positivo = variacao_pct >= 0
    seta = "▲" if positivo else "▼"
    tipo = "ok" if positivo else "warn"
    return badge_html(f"{seta} {abs(variacao_pct):.2f}%", tipo)


def badge_alerta(preco_alvo: float | None, cotacao_atual: float | None, formatar_moeda) -> str:
    if preco_alvo is None:
        return '<span class="texto-apagado">—</span>'
    tem_cotacao = cotacao_atual is not None
    # Alerta de "preço que eu quero comprar": dispara quando a cotação CAI até
    # o preço-alvo (ou abaixo), não quando sobe acima dele — senão qualquer
    # alerta configurado abaixo da cotação atual (o caso normal, já que você
    # quer comprar mais barato) apareceria como "atingido" desde o primeiro
    # instante, mesmo sem o preço ter caído.
    atingido = tem_cotacao and cotacao_atual <= preco_alvo
    texto = f"{'🔔 Atingiu' if atingido else '🔕 Alvo'} {formatar_moeda(preco_alvo)}"
    return badge_html(texto, "info" if atingido else "neutral")


def card_kpi_html(
    rotulo: str, valor: str, cor_valor: str = COR_TEXTO_PRIMARIO, subvalor: str | None = None,
    cor_sub: str = COR_TEXTO_SECUNDARIO, destaque: bool = False, compacto: bool = False,
) -> str:
    """
    `compacto` (2026-09-03, pedido do Diego — divulgação progressiva na
    própria linha de KPIs): usado nos cards secundários (contagens,
    alertas), que devem aparecer sempre visíveis mas menores/discretos,
    sem competir visualmente com os 2-3 números essenciais (Patrimônio,
    Resultado). `destaque` e `compacto` são independentes — não faz
    sentido combinar os dois, mas nada impede.
    """
    sub = f'<div class="subvalor" style="color:{cor_sub}">{subvalor}</div>' if subvalor else ""
    classes = "card-kpi"
    if destaque:
        classes += " destaque"
    if compacto:
        classes += " compacto"
    return (
        f'<div class="{classes}"><span class="rotulo">{rotulo}</span>'
        f'<div class="valor" style="color:{cor_valor}">{valor}</div>{sub}</div>'
    )


def render_cards(cards_html: list[str]) -> None:
    """Renderiza uma linha de cards de resumo lado a lado (grid responsivo)."""
    st.markdown(f'<div class="grid-cards">{"".join(cards_html)}</div>', unsafe_allow_html=True)


def aviso_privacidade_html(mensagem: str) -> str:
    """
    Bloco de aviso "LGPD" (2026-09-03, pedido do Diego): usado no lugar de
    um gráfico com valores em R$ quando `ocultar_valores` está ativo — ver
    `ui/visao_geral.py::_render_graficos_resumo`.
    """
    return f'<div class="aviso-privacidade"><span class="icone">🔒</span>{mensagem}</div>'


def linha_diagnostico_html(rotulo: str, valor: str, cor_valor: str = "#ffffff") -> str:
    """Uma linha do 'Painel de Diagnóstico da Carteira' (rótulo à esquerda, valor à direita)."""
    return (
        f'<div class="linha-diagnostico"><span class="rotulo-diag">{rotulo}</span>'
        f'<span class="valor-diag" style="color:{cor_valor}">{valor}</span></div>'
    )


def painel_diagnostico_html(titulo: str, linhas_html: list[str], selo: str | None = None) -> str:
    """Agrupa várias linha_diagnostico_html() num bloco com título e borda dourada."""
    rodape = f'<div class="selo-fonte">{selo}</div>' if selo else ""
    return f'<div class="painel-diagnostico"><h4>{titulo}</h4>{"".join(linhas_html)}{rodape}</div>'
