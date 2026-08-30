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

from core.config import COR_DESTAQUE, COR_FUNDO_CARD, COR_INFO, COR_NEGATIVO, COR_NEUTRO, COR_POSITIVO

CSS_GLOBAL = f"""
<style>
/* Cards de resumo (KPIs) — mesmo visual do dashboard original, com um
   acabamento "institucional": borda sutil em degradê, leve sombra e uma
   barra superior fina que assume a cor do indicador quando informada
   (COR_DESTAQUE nas leituras mais importantes para o value investing). */
.grid-cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
}}
.card-kpi {{
    background: linear-gradient(180deg, {COR_FUNDO_CARD} 0%, #182230 100%);
    border: 1px solid #313d4f;
    border-radius: 0.85rem;
    padding: 1rem 1.25rem;
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
    font-size: 11px; font-weight: 600; color: #9ca3af;
    text-transform: uppercase; letter-spacing: 0.05em;
}}
.card-kpi .valor {{
    font-size: 1.4rem; font-weight: 700; color: #ffffff; margin-top: 0.25rem;
    font-variant-numeric: tabular-nums;
}}
.card-kpi .subvalor {{ font-size: 12px; font-weight: 500; margin-top: 0.15rem; }}

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
table.tabela-carteira .ticker {{ font-weight: 700; color: #ffffff; }}
table.tabela-carteira .setor {{ font-size: 11px; color: #9ca3af; }}

/* Painel de diagnóstico institucional (Visão Geral) — bloco com destaque
   visual próprio, separado dos cards de KPI comuns. */
.painel-diagnostico {{
    background: linear-gradient(135deg, #1a2233 0%, #161d2b 100%);
    border: 1px solid rgba(212,175,55,0.25);
    border-radius: 0.85rem;
    padding: 1.1rem 1.35rem;
    margin-bottom: 1rem;
}}
.painel-diagnostico h4 {{
    margin: 0 0 0.6rem 0; font-size: 13px; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; color: {COR_DESTAQUE};
}}
.linha-diagnostico {{
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 0.35rem 0; border-bottom: 1px dashed rgba(255,255,255,0.06);
    font-size: 13px;
}}
.linha-diagnostico:last-child {{ border-bottom: none; }}
.linha-diagnostico .rotulo-diag {{ color: #c3cad6; }}
.linha-diagnostico .valor-diag {{ font-weight: 700; color: #ffffff; text-align: right; }}
.selo-fonte {{
    display: inline-block; font-size: 10px; color: #6b7280; margin-top: 0.5rem;
    letter-spacing: 0.02em;
}}
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
    rotulo: str, valor: str, cor_valor: str = "#ffffff", subvalor: str | None = None,
    cor_sub: str = "#9ca3af", destaque: bool = False,
) -> str:
    sub = f'<div class="subvalor" style="color:{cor_sub}">{subvalor}</div>' if subvalor else ""
    classe = "card-kpi destaque" if destaque else "card-kpi"
    return (
        f'<div class="{classe}"><span class="rotulo">{rotulo}</span>'
        f'<div class="valor" style="color:{cor_valor}">{valor}</div>{sub}</div>'
    )


def render_cards(cards_html: list[str]) -> None:
    """Renderiza uma linha de cards de resumo lado a lado (grid responsivo)."""
    st.markdown(f'<div class="grid-cards">{"".join(cards_html)}</div>', unsafe_allow_html=True)


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
