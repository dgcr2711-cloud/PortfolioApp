"""
Indicadores fundamentalistas (P/L, P/VP, Dividend Yield, ROE, margens,
alavancagem, valor de mercado, beta, faixa de 52 semanas) via yfinance —
o tipo de número que um investidor de "value investing" olha antes de
decidir se um preço é uma pechincha ou uma armadilha de valor.

O dashboard HTML original tinha uma aba parecida, mas ela falhava com
frequência porque rodava dentro do navegador e esbarrava em bloqueio de
CORS ao consultar o Yahoo Finance direto. Rodando em Python, no seu
computador, essa restrição não existe — a mesma informação chega de forma
muito mais confiável.

Cacheado por 24h (CACHE_TTL_FUNDAMENTOS_SEGUNDOS): fundamentos de uma
empresa não mudam de um minuto para o outro como um preço, então não faz
sentido buscá-los com a mesma frequência.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

import streamlit as st
import yfinance as yf

from core.config import CACHE_TTL_FUNDAMENTOS_SEGUNDOS, SUFIXO_B3
from core.numeros import numero_valido

# 2026-09-03 — mesmo raciocínio de core.market_data._buscar_em_paralelo:
# cada busca no Yahoo Finance é espera de rede (I/O), não conta de CPU, e
# aqui tem duas fontes de lentidão que valem a pena resolver:
#
# 1. "🔄 Atualizar Fundamentos" buscava um ticker de cada vez, em vez de em
#    paralelo (mesmo problema que atualizar_cotacoes tinha).
# 2. "🔄 Atualizar Análise Avançada" chamava buscar_dados_piotroski() e
#    logo em seguida buscar_dados_altman() para o MESMO ticker — e cada
#    uma abria sua própria conexão e buscava as demonstrações ANUAIS de
#    novo, mesmo as duas precisando quase dos mesmos dados (.financials e
#    .balance_sheet). Ver _buscar_demonstracoes_anuais() abaixo: agora as
#    duas funções compartilham uma única busca cacheada por ticker — a
#    segunda chamada (Piotroski ou Altman, o que rodar depois) vem do
#    cache, sem nova ida à rede.
_REQUISICOES_SIMULTANEAS = 5


def _buscar_em_paralelo(itens: list[str], funcao_busca) -> dict[str, Any]:
    """
    Roda `funcao_busca(item)` para cada item da lista, em até
    _REQUISICOES_SIMULTANEAS threads ao mesmo tempo, e devolve um dict
    {item: resultado} só com os que não vieram None. Uma falha (ou
    exceção) isolada num item não derruba os outros. Mesmo padrão de
    core.market_data._buscar_em_paralelo (não compartilhado entre os dois
    módulos de propósito — é só uma dúzia de linhas, e evita acoplar dois
    módulos que hoje não têm nenhuma outra dependência um do outro).
    """
    resultados: dict[str, Any] = {}
    if not itens:
        return resultados
    with ThreadPoolExecutor(max_workers=min(_REQUISICOES_SIMULTANEAS, len(itens))) as executor:
        futuro_por_item = {executor.submit(funcao_busca, item): item for item in itens}
        for futuro in as_completed(futuro_por_item):
            item = futuro_por_item[futuro]
            try:
                resultado = futuro.result()
            except Exception:
                resultado = None
            if resultado is not None:
                resultados[item] = resultado
    return resultados


_LINHAS_LUCRO_LIQUIDO = ("Net Income", "Net Income Common Stockholders", "Net Income Continuous Operations")
_LINHAS_DIVIDENDOS_PAGOS = ("Cash Dividends Paid", "Common Stock Dividend Paid", "Preferred Stock Dividend Paid")
_LINHAS_DIVIDA_TOTAL = ("Total Debt",)
_LINHAS_CAIXA_TOTAL = ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash Financial")

# Linhas das demonstrações ANUAIS usadas só pelo Piotroski F-Score (ver
# buscar_dados_piotroski abaixo) — nomes diferentes dos de cima porque vêm
# de outra demonstração (balanço/DFC anuais, não a DRE trimestral).
_LINHAS_ATIVOS_TOTAIS = ("Total Assets",)
_LINHAS_FLUXO_CAIXA_OPERACIONAL = ("Operating Cash Flow", "Total Cash From Operating Activities", "Cash Flow From Continuing Operating Activities")
_LINHAS_DIVIDA_LONGO_PRAZO = ("Long Term Debt", "Long Term Debt And Capital Lease Obligation")
_LINHAS_ATIVO_CIRCULANTE = ("Current Assets", "Total Current Assets")
_LINHAS_PASSIVO_CIRCULANTE = ("Current Liabilities", "Total Current Liabilities")
_LINHAS_NUM_ACOES_BALANCO = ("Share Issued", "Ordinary Shares Number", "Common Stock Shares Outstanding")
_LINHAS_RECEITA = ("Total Revenue", "Operating Revenue")
_LINHAS_LUCRO_BRUTO = ("Gross Profit",)

# Linhas usadas só pelo Altman Z-Score (ver buscar_dados_altman abaixo).
_LINHAS_LUCROS_RETIDOS = ("Retained Earnings",)
_LINHAS_EBIT = ("EBIT", "Operating Income")
_LINHAS_PASSIVO_TOTAL = ("Total Liabilities Net Minority Interest", "Total Liab")


def _linha(demonstrativo: Any, nomes_possiveis: tuple[str, ...]) -> Any | None:
    """As demonstrações financeiras do yfinance nem sempre usam o mesmo nome de
    linha pra empresa pra empresa (varia um pouco por setor) — tenta cada nome
    possível e usa o primeiro que existir."""
    if demonstrativo is None or demonstrativo.empty:
        return None
    for nome in nomes_possiveis:
        if nome in demonstrativo.index:
            return demonstrativo.loc[nome]
    return None


def _payout_ttm_calculado(ticker_obj: Any) -> float | None:
    """
    Payout dos últimos 12 meses, CALCULADO por nós a partir das
    demonstrações TRIMESTRAIS (soma o lucro líquido e os dividendos pagos
    dos 4 trimestres mais recentes, depois divide) — em vez de usar o
    "payoutRatio" que o Yahoo Finance já entrega pronto em `.info` (esse
    vai direto no campo "payout_ratio" acima).

    A ideia é ter um segundo número, calculado de forma independente, como
    conferência do primeiro — e trimestres têm uma cobertura de dados bem
    melhor no Yahoo Finance pra empresas da B3 do que anos fiscais fechados
    (a primeira versão disso tentava média de 3 ANOS e ficava "—" com
    frequência; passamos a usar só os últimos 12 meses a pedido do Diego).

    Só devolve um valor quando os 4 trimestres mais recentes têm lucro
    líquido disponível (dividendo ausente num trimestre é tratado como
    zero — muitas empresas da B3 pagam só 1-2 vezes por ano, não é sinal de
    dado faltando) e a soma dos 4 lucros for positiva.
    """
    try:
        lucros_tri = _linha(ticker_obj.quarterly_income_stmt, _LINHAS_LUCRO_LIQUIDO)
        dividendos_tri = _linha(ticker_obj.quarterly_cashflow, _LINHAS_DIVIDENDOS_PAGOS)
    except Exception:
        return None
    if lucros_tri is None:
        return None

    colunas = list(lucros_tri.index)[:4]  # 4 trimestres mais recentes ≈ últimos 12 meses
    if len(colunas) < 4:
        return None

    soma_lucro = 0.0
    soma_dividendo = 0.0
    for coluna in colunas:
        lucro = numero_valido(lucros_tri.get(coluna))
        if lucro is None:
            return None  # trimestre sem lucro reportado -> não dá pra confiar na soma de 12 meses
        soma_lucro += lucro
        if dividendos_tri is not None and coluna in dividendos_tri.index:
            soma_dividendo += numero_valido(dividendos_tri.get(coluna)) or 0.0

    return (abs(soma_dividendo) / soma_lucro) if soma_lucro > 0 else None


def _num_acoes_com_fallback(info: dict[str, Any]) -> float | None:
    """
    'sharesOutstanding' é o campo mais direto pro nº de ações, mas o Yahoo
    Finance costuma deixá-lo vazio com mais frequência pra ações da B3 do
    que pra ações dos EUA. Quando isso acontece, tentamos, nessa ordem:
    'impliedSharesOutstanding' (outro campo que às vezes vem preenchido
    quando o primeiro não vem) e, por último, uma conta equivalente feita
    por nós — Valor de Mercado ÷ preço atual da ação — que chega no MESMO
    número, só que calculado em vez de vir pronto do Yahoo.
    """
    direto = numero_valido(info.get("sharesOutstanding"))
    if direto is not None:
        return direto
    implicito = numero_valido(info.get("impliedSharesOutstanding"))
    if implicito is not None:
        return implicito
    valor_mercado = numero_valido(info.get("marketCap"))
    preco_atual = numero_valido(info.get("currentPrice")) or numero_valido(info.get("regularMarketPrice"))
    if valor_mercado is not None and preco_atual:
        return valor_mercado / preco_atual
    return None


def _divida_liquida_com_fallback(info: dict[str, Any], ticker_obj: Any) -> float | None:
    """
    'totalDebt' e 'totalCash' (o resumo rápido de `.info`) às vezes vêm
    vazios pra ações da B3, mesmo quando a demonstração de balanço
    patrimonial completa (`.balance_sheet`) tem esses números — o Yahoo
    Finance nem sempre preenche o resumo com tudo que tem na demonstração
    detalhada. Por isso, quando o resumo rápido não tem os dois valores,
    tentamos de novo direto na demonstração de balanço (coluna mais
    recente) antes de desistir.
    """
    total_debt = numero_valido(info.get("totalDebt"))
    total_cash = numero_valido(info.get("totalCash"))
    if total_debt is not None and total_cash is not None:
        return total_debt - total_cash

    try:
        balanco = ticker_obj.balance_sheet
    except Exception:
        return None
    divida_bp = _linha(balanco, _LINHAS_DIVIDA_TOTAL)
    caixa_bp = _linha(balanco, _LINHAS_CAIXA_TOTAL)
    if divida_bp is None or caixa_bp is None or divida_bp.empty or caixa_bp.empty:
        return None
    divida_recente = numero_valido(divida_bp.iloc[0])
    caixa_recente = numero_valido(caixa_bp.iloc[0])
    if divida_recente is None or caixa_recente is None:
        return None
    return divida_recente - caixa_recente


def _dividend_yield_fracao(valor: Any) -> float | None:
    """
    Normaliza o "dividendYield" do Yahoo Finance para sempre vir como
    fração (0.08 = 8%), nunca como percentual (8.0). Diferentes versões da
    biblioteca yfinance já devolveram esse campo nos dois formatos — e
    nenhuma ação da bolsa paga 100%+ de dividend yield ao ano, então
    qualquer valor acima de 1.0 quase certamente já veio em formato
    percentual e precisa ser dividido por 100.
    """
    numero = numero_valido(valor)
    if numero is None:
        return None
    return numero / 100 if numero > 1.5 else numero


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTOS_SEGUNDOS, show_spinner=False)
def buscar_fundamentos(ticker: str) -> dict[str, Any] | None:
    """
    Busca os principais indicadores fundamentalistas de um ativo da B3.
    Retorna None se o Yahoo Finance não devolver dados para o ticker.

    Os nomes de campo abaixo ("trailingPE", "priceToBook" etc.) são os
    mesmos que o Yahoo Finance usa internamente — manter o nome original
    facilita comparar com o próprio site do Yahoo se precisar conferir algo.
    """
    symbolo = f"{ticker}{SUFIXO_B3}"
    try:
        ticker_obj = yf.Ticker(symbolo)
        info = ticker_obj.info
    except Exception:
        return None
    if not info or not isinstance(info, dict):
        return None

    return {
        "ticker": ticker,
        "nome": info.get("longName") or info.get("shortName") or ticker,
        "setor_yahoo": info.get("sector"),
        "industria": info.get("industry"),
        # Valuation
        "pl": numero_valido(info.get("trailingPE")),
        "pl_projetado": numero_valido(info.get("forwardPE")),
        "pvp": numero_valido(info.get("priceToBook")),
        "valor_mercado": numero_valido(info.get("marketCap")),
        # LPA (lucro por ação) e VPA (valor patrimonial por ação) — usados
        # pelo "football field" de valuation (core.valuation_multiplos):
        # Número de Graham e Valor Patrimonial por Ação. Já vêm prontos
        # como "por ação" do próprio `.info` do yfinance, sem precisar
        # calcular a partir do balanço/DRE (menos exposto a nomes de linha
        # que variam entre empresas, diferente do que é feito para
        # Piotroski/Altman acima).
        "lpa": numero_valido(info.get("trailingEps")),
        "vpa": numero_valido(info.get("bookValue")),
        # Renda / distribuição
        "dividend_yield": _dividend_yield_fracao(info.get("dividendYield")),
        "payout_ratio": numero_valido(info.get("payoutRatio")),
        "payout_ttm_calculado": _payout_ttm_calculado(ticker_obj),
        # Rentabilidade e qualidade
        "roe": numero_valido(info.get("returnOnEquity")),
        "roa": numero_valido(info.get("returnOnAssets")),
        "margem_liquida": numero_valido(info.get("profitMargins")),
        "margem_bruta": numero_valido(info.get("grossMargins")),
        "crescimento_receita": numero_valido(info.get("revenueGrowth")),
        # Solidez financeira
        "divida_patrimonio": numero_valido(info.get("debtToEquity")),
        "liquidez_corrente": numero_valido(info.get("currentRatio")),
        "free_cashflow": numero_valido(info.get("freeCashflow")),
        # Indicadores usados como ponto de partida na calculadora de Preço
        # Teto (aba 🎯, core.calculations.calcular_fcd): free_cashflow acima
        # já serve de FCF base; estes dois completam dívida líquida e nº de
        # ações — cada um com fallback pra quando o resumo rápido do Yahoo
        # (`.info`) vem incompleto, o que é mais comum em ações da B3.
        "divida_liquida": _divida_liquida_com_fallback(info, ticker_obj),
        "num_acoes": _num_acoes_com_fallback(info),
        # Risco / faixa de preço
        "beta": numero_valido(info.get("beta")),
        "minima_52s": numero_valido(info.get("fiftyTwoWeekLow")),
        "maxima_52s": numero_valido(info.get("fiftyTwoWeekHigh")),
        "atualizadoEm": datetime.now().isoformat(),
    }


def atualizar_fundamentos(tickers: list[str], fundamentos_atuais: dict[str, dict]) -> tuple[dict[str, dict], list[str]]:
    """
    Mesma forma de uso de market_data.atualizar_cotacoes(): busca cada
    ticker (em paralelo — ver _buscar_em_paralelo, 2026-09-03) e devolve
    um dicionário mesclado com o que já existia + a lista de tickers que
    falharam.
    """
    resultados = _buscar_em_paralelo(tickers, buscar_fundamentos)
    novos_fundamentos = dict(fundamentos_atuais)
    novos_fundamentos.update(resultados)
    falhas = [t for t in tickers if t not in resultados]
    return novos_fundamentos, falhas


def limpar_cache_fundamentos() -> None:
    """Força a próxima busca a ignorar o cache de 24h."""
    buscar_fundamentos.clear()


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTOS_SEGUNDOS, show_spinner=False)
def _buscar_demonstracoes_anuais(symbolo_yahoo: str) -> dict[str, Any]:
    """
    Busca, numa ÚNICA sessão do yfinance, tudo que o Piotroski F-Score
    (buscar_dados_piotroski) e o Altman Z-Score (buscar_dados_altman)
    precisam das demonstrações ANUAIS (.financials, .balance_sheet,
    .cashflow) + o resumo rápido (.info, só usado pelo Altman).

    2026-09-03 — antes, cada uma dessas duas funções abria sua PRÓPRIA
    conexão e buscava essas demonstrações de novo, mesmo sendo chamadas
    uma logo depois da outra para o MESMO ticker (ver
    ui.acoes_comuns.atualizar_analise_avancada) — .financials e
    .balance_sheet eram buscados 2x cada, e .info só era usado pelo
    Altman mas ainda assim numa conexão separada. Com essa busca
    compartilhada (cacheada por symbolo), a segunda chamada — Piotroski
    ou Altman, o que rodar por último — vem do cache, sem nova ida à
    rede: na prática, analisar um ticker passou a custar 1 busca de rede
    em vez de quase 2.

    Cada campo é buscado com seu próprio try/except: uma demonstração que
    falhar (ou nem existir para aquele ativo) não derruba as outras —
    fica None só naquele campo específico. Isso é estritamente mais
    tolerante do que o comportamento antigo (onde qualquer uma das três
    falhando descartava as outras duas que tinham funcionado): cada
    consumidor já sabe lidar com um campo faltando (ver _linha()), então
    não há motivo pra jogar fora dados que vieram certos.
    """
    try:
        ticker_obj = yf.Ticker(symbolo_yahoo)
    except Exception:
        return {"info": None, "financials": None, "balance_sheet": None, "cashflow": None}

    def _tentar(obter):
        try:
            return obter()
        except Exception:
            return None

    return {
        "info": _tentar(lambda: ticker_obj.info),
        "financials": _tentar(lambda: ticker_obj.financials),
        "balance_sheet": _tentar(lambda: ticker_obj.balance_sheet),
        "cashflow": _tentar(lambda: ticker_obj.cashflow),
    }


def limpar_cache_demonstracoes_anuais() -> None:
    """Força a próxima busca (Piotroski ou Altman) a ignorar o cache de 24h."""
    _buscar_demonstracoes_anuais.clear()


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTOS_SEGUNDOS, show_spinner=False)
def buscar_dados_piotroski(ticker: str) -> dict[str, Any] | None:
    """
    Busca os números brutos de DOIS anos fiscais (mais recente e anterior)
    que core.piotroski.calcular_piotroski() precisa para montar o F-Score —
    vem das demonstrações ANUAIS do yfinance (balanço, DRE e DFC anuais;
    não as trimestrais usadas em _payout_ttm_calculado acima), porque o
    F-Score compara ano fiscal completo com ano fiscal completo.

    Cada campo que não vier disponível fica None — nunca lança erro nem
    finge um valor. core.piotroski já sabe tratar isso marcando só aquele
    critério específico como "não avaliado", em vez de travar a conta
    inteira ou (pior) contar como se a empresa tivesse ido mal.

    ⚠️ Diferente do resto deste arquivo (já usado e conferido em produção),
    esta função ainda não foi testada com o yfinance de verdade — o sandbox
    onde ela foi escrita não tem a biblioteca instalada. A lógica de
    PONTUAÇÃO (core/piotroski.py) já está com 100% de cobertura de testes
    usando números inventados; o que falta confirmar na prática, rodando no
    seu PC, é só se os nomes de linha abaixo (ex: "Total Assets", "Long
    Term Debt") batem com o que o Yahoo Finance realmente devolve para
    ações da B3 — por isso cada campo tem uma lista de nomes alternativos,
    igual ao padrão já usado em _linha() para os outros campos deste
    arquivo, mas vale conferir o resultado na aba Fundamentos antes de
    confiar de olhos fechados na pontuação de uma ação específica.

    2026-09-03: a busca em si agora vem de _buscar_demonstracoes_anuais()
    (compartilhada com buscar_dados_altman) — ver docstring de lá.
    """
    symbolo = f"{ticker}{SUFIXO_B3}"
    brutos = _buscar_demonstracoes_anuais(symbolo)
    financials = brutos["financials"]
    balanco = brutos["balance_sheet"]
    fluxo_caixa = brutos["cashflow"]

    lucro = _linha(financials, _LINHAS_LUCRO_LIQUIDO)
    ativos = _linha(balanco, _LINHAS_ATIVOS_TOTAIS)
    if lucro is None or ativos is None or len(lucro.index) < 2 or len(ativos.index) < 2:
        # Sem pelo menos 2 anos de lucro líquido E de ativos totais não vale
        # nem a pena tentar montar o resto — praticamente todo critério do
        # F-Score depende de um dos dois.
        return None

    cfo = _linha(fluxo_caixa, _LINHAS_FLUXO_CAIXA_OPERACIONAL)
    divida_lp = _linha(balanco, _LINHAS_DIVIDA_LONGO_PRAZO)
    ativo_circ = _linha(balanco, _LINHAS_ATIVO_CIRCULANTE)
    passivo_circ = _linha(balanco, _LINHAS_PASSIVO_CIRCULANTE)
    num_acoes = _linha(balanco, _LINHAS_NUM_ACOES_BALANCO)
    receita = _linha(financials, _LINHAS_RECEITA)
    lucro_bruto = _linha(financials, _LINHAS_LUCRO_BRUTO)

    def _valor(serie: Any, indice: int) -> float | None:
        """Posição 0 = ano fiscal mais recente, 1 = ano anterior — segue a
        mesma convenção (colunas mais recentes primeiro) já usada em
        _payout_ttm_calculado() acima. None se a série não existir ou não
        tiver essa posição."""
        if serie is None or indice >= len(serie.index):
            return None
        return numero_valido(serie.iloc[indice])

    def _margem_bruta(indice: int) -> float | None:
        bruto = _valor(lucro_bruto, indice)
        rec = _valor(receita, indice)
        if bruto is None or rec is None or rec == 0:
            return None
        return bruto / rec

    divida_lp_atual = _valor(divida_lp, 0)
    divida_lp_anterior = _valor(divida_lp, 1)

    return {
        "lucro_liquido_atual": _valor(lucro, 0),
        "lucro_liquido_anterior": _valor(lucro, 1),
        "ativos_totais_atual": _valor(ativos, 0),
        "ativos_totais_anterior": _valor(ativos, 1),
        "fluxo_caixa_operacional_atual": _valor(cfo, 0),
        # Ausência da linha "Long Term Debt" no balanço do yfinance quase
        # sempre significa que a empresa simplesmente não tem dívida de
        # longo prazo (comum em empresas menores) — não que o dado esteja
        # faltando por erro de busca — por isso o fallback é 0.0 em vez de
        # None (que faria o critério de alavancagem virar "não avaliado"
        # à toa em toda empresa sem dívida de longo prazo).
        "divida_longo_prazo_atual": divida_lp_atual if divida_lp_atual is not None else 0.0,
        "divida_longo_prazo_anterior": divida_lp_anterior if divida_lp_anterior is not None else 0.0,
        "ativo_circulante_atual": _valor(ativo_circ, 0),
        "passivo_circulante_atual": _valor(passivo_circ, 0),
        "ativo_circulante_anterior": _valor(ativo_circ, 1),
        "passivo_circulante_anterior": _valor(passivo_circ, 1),
        "num_acoes_atual": _valor(num_acoes, 0),
        "num_acoes_anterior": _valor(num_acoes, 1),
        "margem_bruta_atual": _margem_bruta(0),
        "margem_bruta_anterior": _margem_bruta(1),
        "receita_atual": _valor(receita, 0),
        "receita_anterior": _valor(receita, 1),
    }


def limpar_cache_piotroski() -> None:
    """Força a próxima busca do Piotroski a ignorar o cache de 24h."""
    buscar_dados_piotroski.clear()
    _buscar_demonstracoes_anuais.clear()  # senão a busca "nova" ainda viria do cache compartilhado


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTOS_SEGUNDOS, show_spinner=False)
def buscar_dados_altman(ticker: str) -> dict[str, Any] | None:
    """
    Busca os números do ano fiscal mais recente que core.altman.calcular_altman()
    precisa para montar o Z-Score — vem do balanço e da DRE anuais do
    yfinance, mais o valor de mercado atual (`.info`, o mesmo campo
    "marketCap" já usado em buscar_fundamentos()). Diferente do Piotroski,
    o Altman usa só o ano mais recente (é uma "foto" de um momento, não uma
    comparação entre dois anos).

    Mesma ressalva de buscar_dados_piotroski() logo acima: esta função
    ainda não foi testada com o yfinance de verdade (o sandbox onde foi
    escrita não tem a biblioteca instalada). A lógica de CÁLCULO
    (core/altman.py) já está 100% coberta por testes com números
    inventados; o que falta confirmar no seu PC é só se os nomes de linha
    abaixo batem com o que o Yahoo Finance devolve para ações da B3.

    2026-09-03: a busca em si agora vem de _buscar_demonstracoes_anuais()
    (compartilhada com buscar_dados_piotroski) — ver docstring de lá.
    """
    symbolo = f"{ticker}{SUFIXO_B3}"
    brutos = _buscar_demonstracoes_anuais(symbolo)
    info = brutos["info"]
    financials = brutos["financials"]
    balanco = brutos["balance_sheet"]
    if not info or not isinstance(info, dict):
        return None

    ativos = _linha(balanco, _LINHAS_ATIVOS_TOTAIS)
    ativo_circ = _linha(balanco, _LINHAS_ATIVO_CIRCULANTE)
    passivo_circ = _linha(balanco, _LINHAS_PASSIVO_CIRCULANTE)
    lucros_retidos = _linha(balanco, _LINHAS_LUCROS_RETIDOS)
    passivo_total = _linha(balanco, _LINHAS_PASSIVO_TOTAL)
    ebit = _linha(financials, _LINHAS_EBIT)
    receita = _linha(financials, _LINHAS_RECEITA)

    def _mais_recente(serie: Any) -> float | None:
        if serie is None or serie.empty:
            return None
        return numero_valido(serie.iloc[0])

    return {
        "ativo_circulante": _mais_recente(ativo_circ),
        "passivo_circulante": _mais_recente(passivo_circ),
        "ativos_totais": _mais_recente(ativos),
        "lucros_retidos": _mais_recente(lucros_retidos),
        "ebit": _mais_recente(ebit),
        "valor_mercado": numero_valido(info.get("marketCap")),
        "passivo_total": _mais_recente(passivo_total),
        "receita": _mais_recente(receita),
    }


def limpar_cache_altman() -> None:
    """Força a próxima busca do Altman Z-Score a ignorar o cache de 24h."""
    buscar_dados_altman.clear()
    _buscar_demonstracoes_anuais.clear()  # senão a busca "nova" ainda viria do cache compartilhado


def buscar_analise_avancada_varios(tickers: list[str]) -> tuple[dict[str, dict], dict[str, dict]]:
    """
    Busca Piotroski + Altman de vários tickers em paralelo (2026-09-03 —
    ver _buscar_em_paralelo no topo do arquivo). Como as duas funções
    compartilham o cache de _buscar_demonstracoes_anuais, buscar as duas
    pro mesmo ticker custa, na prática, só 1 ida à rede (a segunda já vem
    do cache) — este helper só paraleliza ENTRE tickers diferentes, que é
    onde ainda sobrava tempo sequencial.

    Devolve (piotroski_por_ticker, altman_por_ticker) — cada um só com os
    tickers em que aquela busca específica deu certo (um ativo pode ter
    Piotroski sem ter Altman, ou vice-versa; um não depende do outro).
    """
    piotroski_por_ticker: dict[str, dict] = {}
    altman_por_ticker: dict[str, dict] = {}
    if not tickers:
        return piotroski_por_ticker, altman_por_ticker

    def _buscar_os_dois(ticker: str) -> tuple[dict | None, dict | None]:
        """
        Busca Piotroski e Altman independentemente um do outro — mesma
        garantia que o código sequencial antigo já tinha ("um não trava o
        outro", ver docstring de atualizar_analise_avancada em
        ui/acoes_comuns.py): as duas funções documentam que nunca lançam
        exceção (devolvem None em vez disso), mas por segurança uma
        exceção inesperada numa não impede a outra de ser tentada.
        """
        try:
            dados_piotroski = buscar_dados_piotroski(ticker)
        except Exception:
            dados_piotroski = None
        try:
            dados_altman = buscar_dados_altman(ticker)
        except Exception:
            dados_altman = None
        return dados_piotroski, dados_altman

    with ThreadPoolExecutor(max_workers=min(_REQUISICOES_SIMULTANEAS, len(tickers))) as executor:
        futuro_por_ticker = {executor.submit(_buscar_os_dois, ticker): ticker for ticker in tickers}
        for futuro in as_completed(futuro_por_ticker):
            ticker = futuro_por_ticker[futuro]
            try:
                dados_piotroski, dados_altman = futuro.result()
            except Exception:
                continue
            if dados_piotroski is not None:
                piotroski_por_ticker[ticker] = dados_piotroski
            if dados_altman is not None:
                altman_por_ticker[ticker] = dados_altman
    return piotroski_por_ticker, altman_por_ticker
