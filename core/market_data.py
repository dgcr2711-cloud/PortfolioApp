"""
Busca de cotações na B3 via Yahoo Finance, usando a biblioteca `yfinance`.

Por que yfinance? Ele não exige cadastro nem chave de API (token) — só
busca os dados públicos que o próprio site do Yahoo Finance expõe — e é a
forma mais simples de automatizar isso rodando localmente no seu
computador (diferente do dashboard em HTML, que tinha que contornar
bloqueios de CORS do navegador com um proxy).

As funções usam o cache do Streamlit (`st.cache_data`) para não buscar a
mesma cotação repetidamente a cada clique na tela — os dados só ficam
"velhos" por no máximo CACHE_TTL_COTACAO_SEGUNDOS. O botão "🔄 Atualizar
Dados" da barra lateral chama `limpar_cache_cotacoes()` antes de buscar de
novo, então ele sempre força uma consulta nova ao Yahoo Finance.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Any

import requests
import streamlit as st
import yfinance as yf

from core.config import (
    CACHE_TTL_COTACAO_HGBRASIL_SEGUNDOS,
    CACHE_TTL_COTACAO_SEGUNDOS,
    CACHE_TTL_DIVIDENDOS_SEGUNDOS,
    CACHE_TTL_NOME_EMPRESA_SEGUNDOS,
    CACHE_TTL_TAXAS_HGBRASIL_SEGUNDOS,
    CAMINHO_CHAVE_HGBRASIL,
    SUFIXO_B3,
    TICKER_IBOVESPA,
    TIMEOUT_HGBRASIL_SEGUNDOS,
    URL_HGBRASIL_FINANCE,
    URL_HGBRASIL_STOCK_PRICE,
)
from core.numeros import numero_valido

# Yahoo Finance ocasionalmente responde devagar ou recusa uma requisição
# (timeout / limite de taxa) quando várias consultas seguidas são feitas em
# rajada — o que tende a atingir mais os ÚLTIMOS tickers de uma atualização
# (normalmente as empresas-alvo, buscadas depois das posições da carteira).
# Uma segunda tentativa, com uma pequena pausa, resolve a esmagadora maioria
# desses casos sem deixar o botão perceptivelmente mais lento.
_TENTATIVAS_POR_TICKER = 2
_PAUSA_ENTRE_TENTATIVAS_SEGUNDOS = 0.8

# 2026-09-03 — diagnóstico de performance a pedido de Diego: buscar um
# ticker de cada vez (com pausa entre eles) é o principal motivo de
# "Atualizar Dados" demorar quando a carteira tem várias posições/alvos —
# cada busca é ESPERA DE REDE (I/O), não conta de CPU, então rodar várias
# ao mesmo tempo com threads (o GIL do Python não atrapalha aqui, porque a
# thread fica ociosa esperando resposta, não calculando) reduz o tempo
# total quase na mesma proporção do número de tickers, sem precisar de
# infraestrutura nova (fila, Redis etc. — desnecessário numa carteira com
# poucas dezenas de tickers). O limite de simultâneas abaixo já funciona
# como um "rate limit" simples contra o Yahoo Finance, evitando disparar
# tudo de uma vez só.
_REQUISICOES_SIMULTANEAS = 5


def _buscar_em_paralelo(tickers: list[str], funcao_busca) -> dict[str, Any]:
    """
    Roda `funcao_busca(ticker)` para cada ticker da lista, em até
    _REQUISICOES_SIMULTANEAS threads ao mesmo tempo, e devolve um dict
    {ticker: resultado} só com os que não vieram None. Uma falha (ou
    exceção) isolada num ticker não derruba os outros — cada
    `funcao_busca` já trata os próprios erros internamente (ver
    _buscar_preco_yahoo/_buscar_proximo_dividendo_yahoo).
    """
    resultados: dict[str, Any] = {}
    if not tickers:
        return resultados
    with ThreadPoolExecutor(max_workers=min(_REQUISICOES_SIMULTANEAS, len(tickers))) as executor:
        futuro_por_ticker = {executor.submit(funcao_busca, ticker): ticker for ticker in tickers}
        for futuro in as_completed(futuro_por_ticker):
            ticker = futuro_por_ticker[futuro]
            try:
                resultado = futuro.result()
            except Exception:
                resultado = None
            if resultado is not None:
                resultados[ticker] = resultado
    return resultados


def _valor_fast_info(fast_info: Any, *nomes: str) -> float | None:
    """
    `fast_info` do yfinance às vezes usa nomes em camelCase ("lastPrice") e
    às vezes em snake_case ("last_price"), dependendo da versão instalada —
    tentamos os dois formatos, por atributo e por chave, e ignoramos
    qualquer erro (é normal faltar algum campo para certos ativos).
    """
    for nome in nomes:
        valor = None
        try:
            valor = fast_info[nome]
        except Exception:
            valor = getattr(fast_info, nome, None)
        numero = numero_valido(valor)
        if numero is not None:
            return numero
    return None


def _tentar_buscar_preco_yahoo(symbolo_yahoo: str) -> dict[str, float] | None:
    """Uma única tentativa de busca — ver _buscar_preco_yahoo() para o retry."""
    try:
        ticker_yf = yf.Ticker(symbolo_yahoo)

        preco_atual = None
        preco_anterior = None
        try:
            fast = ticker_yf.fast_info
            preco_atual = _valor_fast_info(fast, "lastPrice", "last_price")
            preco_anterior = _valor_fast_info(fast, "previousClose", "previous_close")
        except Exception:
            pass

        if preco_atual is None or preco_anterior is None:
            historico = ticker_yf.history(period="5d", interval="1d")
            fechamentos = [
                v for v in (numero_valido(x) for x in historico["Close"].tolist())
                if v is not None
            ] if not historico.empty else []
            if preco_atual is None and fechamentos:
                preco_atual = fechamentos[-1]
            if preco_anterior is None and len(fechamentos) >= 2:
                preco_anterior = fechamentos[-2]

        if preco_atual is None:
            return None
        return {"preco": preco_atual, "previousClose": preco_anterior}
    except Exception:
        return None


@st.cache_data(ttl=CACHE_TTL_COTACAO_SEGUNDOS, show_spinner=False)
def _buscar_preco_yahoo(symbolo_yahoo: str) -> dict[str, float] | None:
    """
    Busca preço atual e fechamento anterior para um símbolo do Yahoo
    Finance (ex: "PETR4.SA" ou "^BVSP"). Retorna None se não encontrar um
    preço atual válido depois de todas as tentativas.

    Tenta primeiro `fast_info` (mais perto de tempo real). Quando falta
    algum valor ali — ou quando o pregão do dia ainda está em andamento e
    o Yahoo retorna um fechamento "NaN" para hoje — completa com o
    histórico diário, sempre ignorando entradas sem número válido.

    Repete a busca algumas vezes (_TENTATIVAS_POR_TICKER) antes de desistir:
    o Yahoo Finance ocasionalmente recusa ou atrasa uma resposta no meio de
    uma rajada de consultas — como o resultado desta função fica em cache,
    uma falha transitória sem retry ficaria "presa" como erro até o cache
    expirar, mesmo que uma nova tentativa, segundos depois, funcionasse.
    """
    for tentativa in range(1, _TENTATIVAS_POR_TICKER + 1):
        resultado = _tentar_buscar_preco_yahoo(symbolo_yahoo)
        if resultado is not None:
            return resultado
        if tentativa < _TENTATIVAS_POR_TICKER:
            time.sleep(_PAUSA_ENTRE_TENTATIVAS_SEGUNDOS)
    return None


@st.cache_data(ttl=CACHE_TTL_NOME_EMPRESA_SEGUNDOS, show_spinner=False)
def _buscar_nome_empresa(symbolo_yahoo: str) -> str | None:
    """
    Busca o nome da empresa (cacheado por bem mais tempo, pois não muda).
    Separado da busca de preço porque `.info` é uma chamada mais pesada ao
    Yahoo Finance — não vale a pena repeti-la a cada atualização de preço.

    É justamente por ser uma chamada pesada (e só acontecer, de fato, na
    PRIMEIRA vez que um ticker novo é buscado — os demais dias usam o cache
    de 24h) que ela tende a ser a mais sensível a uma rejeição temporária do
    Yahoo; daí o mesmo retry usado na busca de preço.
    """
    for tentativa in range(1, _TENTATIVAS_POR_TICKER + 1):
        try:
            info = yf.Ticker(symbolo_yahoo).info
            nome = info.get("longName") or info.get("shortName")
            if nome:
                return nome
        except Exception:
            pass
        if tentativa < _TENTATIVAS_POR_TICKER:
            time.sleep(_PAUSA_ENTRE_TENTATIVAS_SEGUNDOS)
    return None


def buscar_cotacao_ativo(ticker: str) -> dict[str, Any] | None:
    """
    Busca a cotação de um ativo da B3 pelo ticker (ex: "PETR4", sem sufixo).
    Retorna um dicionário no mesmo formato salvo em dados["cotacoes"][ticker],
    ou None se a busca falhar.
    """
    symbolo = f"{ticker}{SUFIXO_B3}"
    preco_info = _buscar_preco_yahoo(symbolo)
    if preco_info is None:
        return None
    nome = _buscar_nome_empresa(symbolo) or ticker
    return {
        "preco": preco_info["preco"],
        "previousClose": preco_info["previousClose"],
        "nome": nome,
        "fonte": "Yahoo Finance (yfinance)",
        "atualizadoEm": datetime.now().isoformat(),
    }


def buscar_cotacao_ibovespa() -> float | None:
    """Busca o valor atual do Ibovespa (usado no comparativo da aba Evolução)."""
    info = _buscar_preco_yahoo(TICKER_IBOVESPA)
    return info["preco"] if info else None


def atualizar_cotacoes(tickers: list[str], cotacoes_atuais: dict[str, dict]) -> tuple[dict[str, dict], list[str]]:
    """
    Busca a cotação de cada ticker da lista e devolve um novo dicionário de
    cotações (mesclado com o que já existia) e a lista de tickers que
    falharam. Não modifica `cotacoes_atuais` — quem chama decide se salva
    o resultado.

    2026-09-03: as buscas agora rodam em paralelo (ver _buscar_em_paralelo)
    em vez de uma de cada vez com pausa — era o principal motivo de
    "Atualizar Dados" demorar com várias posições/alvos na carteira.
    """
    resultados = _buscar_em_paralelo(tickers, buscar_cotacao_ativo)
    novas_cotacoes = dict(cotacoes_atuais)
    novas_cotacoes.update(resultados)
    falhas = [t for t in tickers if t not in resultados]
    return novas_cotacoes, falhas


def limpar_cache_cotacoes() -> None:
    """Força a próxima busca a ignorar o cache — usado pelo botão 'Atualizar Dados'."""
    _buscar_preco_yahoo.clear()
    _buscar_nome_empresa.clear()


# ==========================================================================
# Próximo Dividendo/JCP previsto (aba Proventos → "Próximos Dividendos")
#
# IMPORTANTE — leia antes de mexer aqui: o Yahoo Finance mantém esse dado
# ("próxima data de dividendo") de forma bem mais completa para ações dos
# EUA do que para a B3. Para muitos ativos brasileiros ele simplesmente não
# existe ou está desatualizado — então retornar None para a maioria dos
# tickers é o comportamento ESPERADO, não um bug. Por isso a busca é
# deliberadamente tolerante: tenta dois campos diferentes do yfinance
# (Ticker.calendar e, se não achar nada ali, Ticker.info) e qualquer falha
# vira "sem previsão" silenciosamente, em vez de erro.
# ==========================================================================

def _extrair_data_do_calendar(ticker_obj: "yf.Ticker") -> date | None:
    """
    `Ticker.calendar` é um dict que, quando o Yahoo Finance tem o dado,
    costuma trazer as chaves "Dividend Date" e/ou "Ex-Dividend Date" — mas
    o formato não é garantido (pode até faltar essas chaves, ou o `calendar`
    inteiro pode vir vazio), daí o `.get()` duplo e o try/except.
    """
    try:
        calendario = ticker_obj.calendar
    except Exception:
        return None
    if not isinstance(calendario, dict):
        return None
    valor = calendario.get("Dividend Date") or calendario.get("Ex-Dividend Date")
    return _normalizar_data_yahoo(valor)


def _extrair_data_do_info(ticker_obj: "yf.Ticker") -> date | None:
    """Fallback: `Ticker.info["exDividendDate"]` (só a data ex, sem data de pagamento — o próprio yfinance não expõe a data de pagamento)."""
    try:
        info = ticker_obj.info
    except Exception:
        return None
    if not isinstance(info, dict):
        return None
    return _normalizar_data_yahoo(info.get("exDividendDate"))


def _normalizar_data_yahoo(valor: Any) -> date | None:
    """O yfinance devolve datas em formatos diferentes dependendo do campo/versão — às vezes `date`/`datetime`, às vezes timestamp Unix (segundos). Normaliza os dois; qualquer outra coisa vira None."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        try:
            return datetime.fromtimestamp(valor).date()
        except (OSError, OverflowError, ValueError):
            return None
    return None


@st.cache_data(ttl=CACHE_TTL_DIVIDENDOS_SEGUNDOS, show_spinner=False)
def _buscar_proximo_dividendo_yahoo(symbolo_yahoo: str) -> str | None:
    """Devolve a data prevista (string ISO, para ficar seguro no cache) ou None. Ver nota no topo desta seção sobre None ser o resultado comum para a B3."""
    for tentativa in range(1, _TENTATIVAS_POR_TICKER + 1):
        try:
            ticker_obj = yf.Ticker(symbolo_yahoo)
            data_prevista = _extrair_data_do_calendar(ticker_obj) or _extrair_data_do_info(ticker_obj)
            if data_prevista is not None:
                return data_prevista.isoformat()
            return None  # consultou com sucesso, mas o Yahoo não tem esse dado — não vale repetir
        except Exception:
            pass
        if tentativa < _TENTATIVAS_POR_TICKER:
            time.sleep(_PAUSA_ENTRE_TENTATIVAS_SEGUNDOS)
    return None


def buscar_proximo_dividendo(ticker: str) -> date | None:
    """Data prevista do próximo dividendo/JCP de um ativo da B3 (ex: 'PETR4'), ou None se o Yahoo Finance não tiver esse dado (comum — ver nota no topo desta seção)."""
    symbolo = f"{ticker}{SUFIXO_B3}"
    resultado = _buscar_proximo_dividendo_yahoo(symbolo)
    return date.fromisoformat(resultado) if resultado else None


def buscar_proximos_dividendos(tickers: list[str]) -> list[dict[str, Any]]:
    """
    Busca a data prevista do próximo dividendo/JCP para cada ticker da
    lista (em paralelo — ver _buscar_em_paralelo, 2026-09-03). Só os
    ativos em que o Yahoo Finance tem esse dado aparecem no resultado —
    uma lista bem menor que o total de tickers é normal (ver nota no topo
    desta seção). Ordenado pela data mais próxima primeiro.
    """
    datas_por_ticker = _buscar_em_paralelo(tickers, buscar_proximo_dividendo)
    encontrados = [
        {"ticker": ticker, "data_prevista": data_prevista.isoformat()}
        for ticker, data_prevista in datas_por_ticker.items()
    ]
    encontrados.sort(key=lambda d: d["data_prevista"])
    return encontrados


def limpar_cache_dividendos() -> None:
    """Força a próxima busca de 'Próximos Dividendos' a ignorar o cache — usado pelo botão dedicado na aba Proventos (separado do 'Atualizar Dados' de propósito, pra não deixar ele mais lento)."""
    _buscar_proximo_dividendo_yahoo.clear()


# ==========================================================================
# HG Brasil Finance (2026-09-03)
#
# Duas coisas novas, pedidas por Diego:
#   1. Taxas SELIC/CDI — o Yahoo Finance não tem esse dado; a HG Brasil tem,
#      no endpoint "geral" (disponível pra qualquer chave, inclusive grátis).
#   2. Cotações de ações/FIIs como PLANO B — só usadas para os tickers em
#      que o Yahoo Finance (fonte principal, já testada e gratuita) não
#      conseguiu responder. Isso é de propósito: o endpoint de cotação
#      individual da HG Brasil ("stock_price") exige um plano pago acima do
#      gratuito — se a conta configurada não tiver esse plano, a API
#      simplesmente devolve um erro, e o código abaixo trata isso como "sem
#      resultado" (nunca quebra o app por causa disso, igual a qualquer
#      outra fonte de dado externa neste projeto).
#
# Cache: "simples, por timestamp" (pedido explícito), em vez do decorador
# @st.cache_data usado pelo Yahoo Finance acima — assim estas funções
# também funcionam fora de um app Streamlit (ex: um script de segundo
# plano), sem precisar de contexto nenhum do Streamlit.
# ==========================================================================

_cache_taxas_economicas: dict[str, Any] = {"valor": None, "buscado_em": 0.0}
_cache_cotacoes_hgbrasil: dict[str, dict[str, Any]] = {}  # ticker -> {"valor": {...}, "buscado_em": float}


def _obter_chave_hgbrasil() -> str | None:
    """
    Busca a chave da API HG Brasil, tentando nesta ordem (mesmo padrão de
    core/cloud_sync.py para a chave do Firebase):
      1. Arquivo local ~/.portfolio_b3_secrets/hgbrasil_api_key.json — uso
         normal no seu PC, criado por "Configurar Chave HG Brasil.bat".
      2. Variável de ambiente HGBRASIL_API_KEY — script de segundo plano
         no GitHub Actions.
      3. Secrets do Streamlit Cloud, seção [hgbrasil] — dashboard hospedado.
    Devolve None sem erro nenhum se não encontrar em lugar nenhum (a HG
    Brasil simplesmente não é usada, e o app continua funcionando 100%
    normalmente só com o Yahoo Finance).
    """
    if CAMINHO_CHAVE_HGBRASIL.exists():
        try:
            with open(CAMINHO_CHAVE_HGBRASIL, "r", encoding="utf-8") as f:
                conteudo = json.load(f)
            chave = conteudo.get("api_key")
            if chave:
                return str(chave)
        except (OSError, json.JSONDecodeError):
            pass

    import os

    chave_ambiente = os.environ.get("HGBRASIL_API_KEY")
    if chave_ambiente:
        return chave_ambiente

    try:
        if "hgbrasil" in st.secrets:
            chave_streamlit = st.secrets["hgbrasil"].get("api_key")
            if chave_streamlit:
                return str(chave_streamlit)
    except Exception:
        pass

    return None


def buscar_taxas_economicas() -> dict[str, Any] | None:
    """
    Busca as taxas SELIC e CDI mais recentes na HG Brasil (endpoint geral,
    disponível para qualquer chave). Resultado cacheado por
    CACHE_TTL_TAXAS_HGBRASIL_SEGUNDOS (essas taxas não mudam durante o dia).

    Devolve None em qualquer situação em que não dê pra usar (chave não
    configurada, sem internet, formato inesperado da resposta) — nunca
    lança exceção, para nunca travar "🔄 Atualizar Dados" por causa disso.
    """
    agora = time.time()
    if (
        _cache_taxas_economicas["valor"] is not None
        and (agora - _cache_taxas_economicas["buscado_em"]) < CACHE_TTL_TAXAS_HGBRASIL_SEGUNDOS
    ):
        return _cache_taxas_economicas["valor"]

    chave = _obter_chave_hgbrasil()
    if not chave:
        return None

    try:
        resposta = requests.get(
            URL_HGBRASIL_FINANCE, params={"key": chave}, timeout=TIMEOUT_HGBRASIL_SEGUNDOS
        )
        if resposta.status_code != 200:
            return None
        corpo = resposta.json()
        taxas = (corpo.get("results") or {}).get("taxes")
        if not taxas:
            return None
        # A HG Brasil devolve uma lista com a taxa mais recente primeiro —
        # pegamos o primeiro item, mas de forma defensiva (funciona também
        # se algum dia vier só um dict solto, sem lista).
        taxa_mais_recente = taxas[0] if isinstance(taxas, list) else taxas
        selic = numero_valido(taxa_mais_recente.get("selic"))
        cdi = numero_valido(taxa_mais_recente.get("cdi"))
        if selic is None and cdi is None:
            return None
        resultado = {
            "selic": selic,
            "cdi": cdi,
            "data": taxa_mais_recente.get("date"),
            "atualizadoEm": datetime.now().isoformat(),
            "fonte": "HG Brasil Finance",
        }
    except Exception:
        return None

    _cache_taxas_economicas["valor"] = resultado
    _cache_taxas_economicas["buscado_em"] = agora
    return resultado


def limpar_cache_taxas_economicas() -> None:
    """Força a próxima busca de SELIC/CDI a ignorar o cache."""
    _cache_taxas_economicas["valor"] = None
    _cache_taxas_economicas["buscado_em"] = 0.0


def _extrair_resultados_stock_price(corpo: dict[str, Any]) -> list[dict[str, Any]]:
    """
    A resposta de /finance/stock_price vem como um dict único em
    results (uma consulta de 1 símbolo) OU uma lista de dicts em results
    (vários símbolos de uma vez) — normaliza pros dois casos sempre virarem
    uma lista.
    """
    resultados = corpo.get("results")
    if resultados is None:
        return []
    if isinstance(resultados, list):
        return resultados
    if isinstance(resultados, dict):
        # Pode vir como {"PETR4": {...}, "VALE3": {...}} OU como um único
        # objeto de ativo direto (tem "symbol" na própria raiz) — os dois
        # formatos já foram vistos em integrações parecidas com essa API.
        if "symbol" in resultados:
            return [resultados]
        return list(resultados.values())
    return []


def buscar_cotacoes_hgbrasil(tickers: list[str]) -> dict[str, dict[str, Any]]:
    """
    Busca cotações de ações/FIIs na HG Brasil, numa ÚNICA requisição para
    todos os tickers (economiza franquia da API, ao contrário de uma
    chamada por ticker). Usado só como PLANO B — ver comentário no topo
    desta seção — para os tickers que o Yahoo Finance não conseguiu buscar.

    Devolve um dict {ticker: {preco, previousClose, nome, fonte,
    atualizadoEm}} no mesmo formato de buscar_cotacao_ativo() — só com os
    tickers que a HG Brasil conseguiu responder. Lista vazia/dict vazio em
    qualquer falha (chave não configurada, sem internet, plano da conta não
    inclui esse endpoint, formato inesperado) — nunca lança exceção.
    """
    if not tickers:
        return {}

    chave_cache = ",".join(sorted(tickers))
    agora = time.time()
    entrada_cache = _cache_cotacoes_hgbrasil.get(chave_cache)
    if entrada_cache is not None and (agora - entrada_cache["buscado_em"]) < CACHE_TTL_COTACAO_HGBRASIL_SEGUNDOS:
        return entrada_cache["valor"]

    chave = _obter_chave_hgbrasil()
    if not chave:
        return {}

    try:
        resposta = requests.get(
            URL_HGBRASIL_STOCK_PRICE,
            params={"key": chave, "symbol": ",".join(tickers)},
            timeout=TIMEOUT_HGBRASIL_SEGUNDOS,
        )
        if resposta.status_code != 200:
            # Comum aqui: conta sem o plano necessário para este endpoint
            # (ver comentário no topo da seção) — tratado como "sem
            # resultado", não como erro.
            return {}
        corpo = resposta.json()
        itens = _extrair_resultados_stock_price(corpo)

        resultado: dict[str, dict[str, Any]] = {}
        for item in itens:
            simbolo = item.get("symbol")
            preco = numero_valido(item.get("price"))
            if not simbolo or preco is None:
                continue
            variacao = numero_valido(item.get("change_price"))
            previous_close = (preco - variacao) if variacao is not None else None
            resultado[simbolo] = {
                "preco": preco,
                "previousClose": previous_close,
                "nome": item.get("name") or simbolo,
                "fonte": "HG Brasil Finance",
                "atualizadoEm": datetime.now().isoformat(),
            }
    except Exception:
        return {}

    _cache_cotacoes_hgbrasil[chave_cache] = {"valor": resultado, "buscado_em": agora}
    return resultado


def limpar_cache_cotacoes_hgbrasil() -> None:
    """Força a próxima busca de cotações-plano-B na HG Brasil a ignorar o cache."""
    _cache_cotacoes_hgbrasil.clear()
