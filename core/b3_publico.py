"""
Proventos anunciados oficialmente, buscados DIRETO do site da própria B3 —
sem StatusInvest, sem sites de RI de cada empresa, sem digitar nada.

De onde vem o dado
-------------------
A própria B3 mantém, para cada empresa listada, uma página pública
"Empresas Listadas" (a mesma que qualquer pessoa acessa em
b3.com.br/pt_br/produtos-e-servicos/... > Empresas Listadas > aba "Eventos
Corporativos"). Essa página busca os dados de um endereço técnico da B3
que devolve a informação pronta, em formato JSON — sem exigir login nem
cadastro:

    https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetListedSupplementCompany/<parâmetros em base64>

Os "parâmetros em base64" são só `{"issuingCompany": "PETR", "language":
"pt-br"}` (o código de 4 letras do ticker, sem o número — ex: "PETR" para
PETR4) codificado em base64. Encontramos esse endereço observando, com um
navegador de verdade, quais pedidos a própria página oficial da B3 faz por
trás dos panos — não é documentado publicamente pela B3 como uma "API"
formal (é só como o próprio site funciona), mas também não é scraping de
HTML: é uma resposta JSON pronta, direto do sistema da B3.

O que essa resposta traz, por empresa: todo dividendo, JCP (juros sobre
capital próprio) e rendimento aprovado/anunciado nos últimos ~12-14 meses,
com o VALOR POR AÇÃO exato e a data de pagamento — já é isso que a aba
"Próximos Dividendos" precisa, e é um dado oficial (não uma estimativa).

O que essa resposta NÃO traz: histórico de vários anos (só o ciclo mais
recente) e a posição/carteira do investidor (isso é uma API completamente
diferente da B3, destinada só a instituições — ver conversa no app).

Confiabilidade — leia antes de mexer aqui: como esse endereço não é uma
API oficialmente documentada, o site sistemaswebb3-listados.b3.com.br fica
atrás de uma proteção contra robôs (Cloudflare). Não temos garantia de que
uma consulta simples (sem navegador de verdade) sempre vai passar por essa
proteção — por isso TODA falha aqui (erro de rede, bloqueio, formato
inesperado) é tratada como "esse ativo ficou sem esse dado agora", nunca
como um erro que trava o app. Se um dia isso passar a falhar sempre, é
sinal de que a B3 reforçou o bloqueio, e o app volta a funcionar
normalmente sem essa automação (é só uma tabela a menos).
"""

from __future__ import annotations

import base64
import json
import time
from datetime import date, datetime
from typing import Any

import requests

_URL_BASE = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetListedSupplementCompany/"

_CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://sistemaswebb3-listados.b3.com.br/listedCompaniesPage/main",
}

_TIMEOUT_SEGUNDOS = 12
_PAUSA_ENTRE_TICKERS_SEGUNDOS = 0.4

# Só esses três "label" da B3 viram proventos EM DINHEIRO no app — os
# demais campos da resposta (stockDividends = bonificação/desdobramento,
# subscriptions = subscrição) não são dinheiro recebido e ficam de fora
# de propósito (mesmo critério já usado no resto do app: bonificação é
# evento societário, não provento).
_TIPOS_PROVENTO: dict[str, str] = {
    "DIVIDENDO": "Dividendo",
    "JRS CAP PROPRIO": "JCP",
    "RENDIMENTO": "Rendimento",
}


def extrair_prefixo_ticker(ticker: str) -> str:
    """
    O "código" que a B3 usa nesse sistema é só as letras do ticker, sem o
    número final (ex: "PETR4" -> "PETR", "KLBN4" -> "KLBN"). Sempre as 4
    primeiras letras — vale para toda ação/unit comum da B3; BDRs e alguns
    ativos fora do padrão podem não ter esse mesmo código e simplesmente
    não vão ser encontrados (retornam lista vazia, não erro).
    """
    return ticker.strip().upper()[:4]


def _montar_url(ticker: str) -> str:
    payload = json.dumps(
        {"issuingCompany": extrair_prefixo_ticker(ticker), "language": "pt-br"},
        separators=(",", ":"),
    )
    parametro = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return _URL_BASE + parametro


def _parsear_valor_br(valor_str: Any) -> float | None:
    """Números da B3 vêm como texto, no formato brasileiro (ex: "1.222.000,50")."""
    if not isinstance(valor_str, str) or not valor_str.strip():
        return None
    limpo = valor_str.strip().replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def _parsear_data_br(data_str: Any) -> str | None:
    """"dd/mm/aaaa" -> "aaaa-mm-dd". "31/12/9999" (data "sem fim") e qualquer formato inválido viram None."""
    if not isinstance(data_str, str) or not data_str.strip():
        return None
    try:
        convertida = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None
    if convertida.year >= 9999:
        return None
    return convertida.isoformat()


def _parsear_cash_dividends(payload_bruto: Any, ticker: str) -> list[dict[str, Any]]:
    """
    Função pura: recebe o JSON já decodificado (como `requests` devolveria
    de `.json()`) e devolve a lista de proventos em dinheiro no formato
    interno do app. Não faz nenhuma chamada de rede — só é testável
    isoladamente por causa disso.
    """
    if isinstance(payload_bruto, list):
        item = payload_bruto[0] if payload_bruto else None
    else:
        item = payload_bruto
    if not isinstance(item, dict):
        return []

    resultado = []
    for entrada in item.get("cashDividends") or []:
        tipo = _TIPOS_PROVENTO.get((entrada.get("label") or "").strip())
        if tipo is None:
            continue
        data_pagamento = _parsear_data_br(entrada.get("paymentDate"))
        valor = _parsear_valor_br(entrada.get("rate"))
        if data_pagamento is None or valor is None:
            continue
        resultado.append({
            "ticker": ticker,
            "tipo": tipo,
            "valor_por_acao": valor,
            "data_pagamento": data_pagamento,
            "data_com": _parsear_data_br(entrada.get("lastDatePrior")),
            "relacionado_a": entrada.get("relatedTo") or "",
            "aprovado_em": _parsear_data_br(entrada.get("approvedOn")),
        })
    resultado.sort(key=lambda p: p["data_pagamento"])
    return resultado


def _buscar_json_bruto(ticker: str) -> tuple[bool, Any]:
    """
    (True, payload) se conseguiu buscar e decodificar a resposta da B3;
    (False, None) em QUALQUER falha (sem internet, bloqueio do site,
    HTTP diferente de 200, JSON inválido). Separado de
    buscar_proventos_anunciados() para que quem chama vários tickers em
    sequência consiga distinguir "essa empresa não tem nada anunciado"
    (sucesso, lista vazia) de "não consegui nem falar com o site da B3"
    (falha) — ver buscar_proventos_anunciados_varios().
    """
    try:
        resposta = requests.get(_montar_url(ticker), headers=_CABECALHOS, timeout=_TIMEOUT_SEGUNDOS)
        if resposta.status_code != 200:
            return False, None
        return True, resposta.json()
    except Exception:
        return False, None


def buscar_proventos_anunciados(ticker: str) -> list[dict[str, Any]]:
    """
    Busca, direto no site da B3, os proventos em dinheiro anunciados para
    um ticker (últimos ~12-14 meses, incluindo já pagos e ainda futuros).
    Qualquer falha (rede, bloqueio, formato inesperado) devolve lista
    vazia silenciosamente — nunca lança exceção, para não travar o app.
    """
    sucesso, payload_bruto = _buscar_json_bruto(ticker)
    if not sucesso:
        return []
    return _parsear_cash_dividends(payload_bruto, ticker)


def buscar_proventos_anunciados_varios(tickers: list[str]) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    """
    Busca vários tickers em sequência (com uma pequena pausa entre eles,
    igual ao resto do app, pra não disparar tudo em rajada).

    Devolve (resultado, sem_conexao). `resultado` só tem os tickers em que
    algo foi encontrado. `sem_conexao` fica True quando NENHUM ticker
    consultado conseguiu nem falar com o site da B3 (todos falharam ao
    nível de conexão/bloqueio) — é o sinal para a tela mostrar "não
    consegui acessar o site da B3 agora", em vez de deixar parecer que
    nenhum ativo tem provento anunciado. Com pelo menos um ticker
    respondido normalmente (mesmo que sem nada encontrado), sem_conexao
    fica False. Lista de tickers vazia também devolve sem_conexao False
    (não houve nem tentativa de conexão).
    """
    resultado: dict[str, list[dict[str, Any]]] = {}
    algum_sucesso = False
    for indice, ticker in enumerate(tickers):
        if indice > 0:
            time.sleep(_PAUSA_ENTRE_TICKERS_SEGUNDOS)
        sucesso, payload_bruto = _buscar_json_bruto(ticker)
        if sucesso:
            algum_sucesso = True
            encontrados = _parsear_cash_dividends(payload_bruto, ticker)
            if encontrados:
                resultado[ticker] = encontrados
    sem_conexao = bool(tickers) and not algum_sucesso
    return resultado, sem_conexao


def proximos_a_partir_de(anunciados_por_ticker: dict[str, list[dict]], hoje: date) -> list[dict[str, Any]]:
    """
    Achata o resultado de buscar_proventos_anunciados_varios() numa única
    lista de "próximos dividendos" (só datas de pagamento a partir de
    hoje, inclusive), ordenada pela data mais próxima primeiro.
    """
    hoje_iso = hoje.isoformat()
    proximos = [
        item
        for lista in anunciados_por_ticker.values()
        for item in lista
        if item["data_pagamento"] >= hoje_iso
    ]
    proximos.sort(key=lambda p: p["data_pagamento"])
    return proximos


def precisa_atualizar(atualizado_em_iso: str | None, agora: datetime, intervalo_segundos: float) -> bool:
    """
    True se a busca automática de proventos anunciados nunca rodou com
    sucesso, ou se já se passou `intervalo_segundos` desde a última vez —
    usado por ui/acoes_comuns.py pra decidir se "🔄 Atualizar Dados" deve
    ir até o site da B3 de novo dessa vez, ou pular (dado ainda "fresco").
    Qualquer valor inválido em `atualizado_em_iso` conta como "nunca
    atualizou" (True), pra nunca travar a automação por causa de um dado
    corrompido/inesperado.
    """
    if not atualizado_em_iso:
        return True
    try:
        ultima_atualizacao = datetime.fromisoformat(atualizado_em_iso)
    except ValueError:
        return True
    return (agora - ultima_atualizacao).total_seconds() >= intervalo_segundos


def meses_anunciados_por_ticker(
    anunciados_por_ticker: dict[str, list[dict]], data_minima: str | None = None
) -> dict[str, list[int]]:
    """
    Para cada ticker, em quais meses (1 a 12) a B3 já anunciou algum
    pagamento nesse ciclo mais recente — usado para "acender" células no
    Mapa de Dividendos automaticamente, sem depender do que foi registrado
    manualmente. Meses em ordem crescente, sem repetição.

    `data_minima` (opcional, formato "AAAA-MM-DD"): ignora pagamentos com
    data anterior a essa data — a B3 traz até ~12-14 meses de histórico
    por empresa, o que pode incluir pagamentos de antes de você sequer ter
    aquele ativo (ver core.config.DATA_INICIO_CARTEIRA).
    """
    resultado: dict[str, list[int]] = {}
    for ticker, lista in anunciados_por_ticker.items():
        datas_validas = [
            item["data_pagamento"] for item in lista
            if not data_minima or item["data_pagamento"] >= data_minima
        ]
        meses = sorted({date.fromisoformat(d).month for d in datas_validas})
        if meses:
            resultado[ticker] = meses
    return resultado
