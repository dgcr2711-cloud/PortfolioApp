"""
Unificação das duas fontes de setor que o app tinha (pedido da auditoria):

1. `dados["setores"]` — setor escolhido À MÃO por você (aba Carteira,
   "⚙️ Definir setor de um ativo"), na lista SETORES_PADRAO (em português,
   pensada para a B3). É esta que sempre valeu para diversificação
   setorial, HHI e a tabela da Carteira.
2. `f["setor_yahoo"]` — setor que o Yahoo Finance devolve sozinho ao
   buscar fundamentos (core/fundamentals.py), em inglês e numa
   classificação genérica (GICS), pensada para o mercado americano — só
   aparecia na aba Fundamentos, podendo mostrar um setor DIFERENTE do que
   a Carteira/Visão Geral mostravam para o mesmo ativo.

Em vez de escolher uma das duas fontes e descartar a outra, este módulo
traduz o setor do Yahoo para o mais próximo em SETORES_PADRAO e usa isso
como SUGESTÃO AUTOMÁTICA — só preenche `dados["setores"][ticker]` quando
você ainda não escolheu nada para aquele ativo (nunca sobrescreve uma
escolha sua). Dali em diante, `dados["setores"]` continua sendo a ÚNICA
fonte usada em todo o app — a inconsistência acaba porque só existe mais
um lugar para ler o setor de um ativo.

A tradução é aproximada de propósito: a classificação do Yahoo (pensada
para o mercado americano) não tem uma correspondência exata para
categorias bem brasileiras como "Agronegócio" ou "Papel e Celulose" — por
isso continua sendo só uma SUGESTÃO inicial, sempre revisável à mão na
aba Carteira.
"""

from __future__ import annotations

from core.config import SETORES_PADRAO

# Setor do Yahoo (GICS, em inglês) -> categoria mais próxima em SETORES_PADRAO.
# Yahoo não distingue "Bancos" dentro de "Financial Services" nem tem
# categorias específicas para Agronegócio/Papel e Celulose/Educação/Transporte
# — nesses casos a sugestão fica no genérico mais razoável, e cabe a você
# refinar manualmente se quiser mais precisão (ex: trocar "Industrial" por
# "Transporte e Logística" para uma empresa de logística específica).
_MAPA_SETOR_YAHOO_PARA_PADRAO: dict[str, str] = {
    "energy": "Petróleo e Gás",
    "basic materials": "Mineração e Siderurgia",
    "materials": "Mineração e Siderurgia",
    "financial services": "Bancos",
    "financial": "Bancos",
    "consumer cyclical": "Varejo",
    "consumer defensive": "Varejo",
    "consumer discretionary": "Varejo",
    "consumer staples": "Varejo",
    "utilities": "Energia Elétrica/Saneamento",
    "healthcare": "Saúde",
    "health care": "Saúde",
    "technology": "Tecnologia",
    "information technology": "Tecnologia",
    "industrials": "Industrial",
    "communication services": "Telecomunicações",
    "telecommunication services": "Telecomunicações",
    "real estate": "Imobiliário",
}


def sugerir_setor_a_partir_do_yahoo(setor_yahoo: str | None) -> str | None:
    """
    Traduz o setor bruto do Yahoo (ex: "Energy") para o mais próximo em
    SETORES_PADRAO (ex: "Petróleo e Gás"). Devolve None se `setor_yahoo`
    vier vazio ou não tiver uma correspondência conhecida — nesse caso é
    melhor não sugerir nada do que sugerir "Outros" às cegas.
    """
    if not setor_yahoo:
        return None
    sugestao = _MAPA_SETOR_YAHOO_PARA_PADRAO.get(setor_yahoo.strip().lower())
    if sugestao and sugestao in SETORES_PADRAO:
        return sugestao
    return None


def preencher_setores_sugeridos(dados: dict) -> int:
    """
    Para cada ativo com fundamentos já buscados (`dados["fundamentos"]`)
    que AINDA não tem um setor manual definido, preenche
    `dados["setores"][ticker]` com a sugestão baseada no Yahoo — nunca
    sobrescreve um setor que você já escolheu. Devolve quantos tickers
    foram preenchidos (para a tela poder avisar "sugeri o setor de N
    ativos novos, revise se quiser em ⚙️ Definir setor de um ativo").

    Chamado depois de buscar fundamentos (ui/acoes_comuns.py) — nunca na
    leitura/exibição, para não preencher `dados["setores"]" com valores
    "fantasmas" antes de decidir salvar de verdade.
    """
    setores = dados.setdefault("setores", {})
    fundamentos = dados.get("fundamentos", {})
    preenchidos = 0
    for ticker, f in fundamentos.items():
        if setores.get(ticker):
            continue  # já tem um setor manual (ou uma sugestão anterior) — nunca sobrescreve
        sugestao = sugerir_setor_a_partir_do_yahoo(f.get("setor_yahoo"))
        if sugestao:
            setores[ticker] = sugestao
            preenchidos += 1
    return preenchidos
