"""
Beta e Índice de Sharpe aproximados da carteira — duas métricas clássicas
de risco, calculadas a partir dos MESMOS snapshots de patrimônio que já
alimentam o gráfico de Evolução e o comparativo com o Ibovespa (TWR) —
dados["historico"], um ponto por dia em que "🔄 Atualizar Dados" foi
clicado. NÃO é uma série de retornos diários "de verdade" (isso exigiria
guardar um snapshot todo santo dia útil, o que o app não faz).

- Beta: o quanto a carteira costuma se mover em relação ao Ibovespa (beta
  = 1: se move junto; > 1: mais volátil que o mercado; < 1: menos volátil;
  negativo: tende a se mover na direção OPOSTA — raro numa carteira de
  ações comuns, mas matematicamente possível).
- Índice de Sharpe: o retorno em excesso sobre uma taxa livre de risco (ex:
  CDI/Selic do período — informada por VOCÊ, o app não busca isso
  sozinho), dividido pela volatilidade da carteira. Quanto maior, melhor o
  retorno obtido POR UNIDADE DE RISCO assumido — não é a mesma coisa que
  "quanto rendeu": duas carteiras com o mesmo retorno podem ter Sharpe bem
  diferente se uma balançou muito mais que a outra pelo caminho.

⚠️ APROXIMAÇÃO IMPORTANTE: como os snapshots não são diários, este módulo
trata cada intervalo entre dois snapshots consecutivos como "um período" e
anualiza o Sharpe usando o intervalo MÉDIO observado entre eles — assume um
ritmo razoavelmente regular de atualizações. Quanto mais irregular o ritmo
(ex: dias seguidos e depois semanas sem atualizar), menos preciso o número
fica. O ajuste por aporte/retirada usa o MESMO raciocínio já empregado em
core.calculations.twr_vs_ibovespa e core.portfolio_analytics.cagr_aproximado
— sem isso, um aporte grande entre dois snapshots pareceria "a carteira
valorizou muito", o que não é verdade.

Módulo PURO: só recebe a lista de snapshots já salva (e a taxa livre de
risco, informada manualmente) — não fala com o Yahoo Finance nem com
nenhuma fonte externa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

# Precisa de pelo menos 3 retornos (= 4 snapshots com Ibovespa) para que
# variância/covariância amostral (divisor n-1) façam algum sentido — com
# menos que isso, o número sairia tecnicamente calculável mas
# estatisticamente sem nenhum significado.
MINIMO_RETORNOS_PARA_CALCULAR = 3

# Limiar para tratar uma variância/desvio-padrão como "efetivamente zero".
# Comparar com == 0.0 exato é frágil: séries com retorno idêntico em todos
# os períodos (ex: 1% toda vez) ainda acumulam ruído de ponto flutuante da
# ordem de 1e-34 em vez de exatamente zero — o que faria a divisão explodir
# num número gigante sem sentido (testado e comprovado antes desta
# constante existir) em vez de devolver None como deveria.
_EPSILON_VARIANCIA = 1e-12


@dataclass
class ResultadoRisco:
    beta: float | None
    sharpe_anualizado: float | None
    numero_periodos: int
    dias_cobertos: int | None
    aviso: str | None = None


def _retornos_carteira_e_ibov(historico: list[dict[str, Any]]) -> tuple[list[float], list[float], list[int]]:
    """
    Três listas paralelas — retorno da carteira por período (ajustado por
    aporte/retirada, mesma fórmula de twr_vs_ibovespa), retorno simples do
    Ibovespa no mesmo período, e o número de dias de cada intervalo — só
    considerando snapshots que TÊM Ibovespa registrado (snapshots antigos,
    de antes dessa informação ser salva, não têm) e intervalos com pelo
    menos 1 dia de diferença (dois snapshots no mesmo dia não formam um
    período válido para esta conta).
    """
    com_ibov = [h for h in historico if h.get("ibov")]
    retornos_carteira: list[float] = []
    retornos_ibov: list[float] = []
    dias_intervalos: list[int] = []

    for anterior, atual in zip(com_ibov, com_ibov[1:]):
        if anterior["totalAtual"] <= 0 or anterior["ibov"] <= 0:
            continue
        dias = (date.fromisoformat(atual["data"][:10]) - date.fromisoformat(anterior["data"][:10])).days
        if dias <= 0:
            continue
        fluxo_caixa = atual["totalInvestido"] - anterior["totalInvestido"]
        retorno_carteira = (atual["totalAtual"] - anterior["totalAtual"] - fluxo_caixa) / anterior["totalAtual"]
        retorno_ibov = (atual["ibov"] - anterior["ibov"]) / anterior["ibov"]
        retornos_carteira.append(retorno_carteira)
        retornos_ibov.append(retorno_ibov)
        dias_intervalos.append(dias)

    return retornos_carteira, retornos_ibov, dias_intervalos


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores)


def _variancia_amostral(valores: list[float], media: float) -> float:
    n = len(valores)
    if n < 2:
        return 0.0
    return sum((v - media) ** 2 for v in valores) / (n - 1)


def _covariancia_amostral(a: list[float], b: list[float], media_a: float, media_b: float) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    return sum((a[i] - media_a) * (b[i] - media_b) for i in range(n)) / (n - 1)


def calcular_beta(historico: list[dict[str, Any]]) -> float | None:
    """Beta = Cov(retorno_carteira, retorno_ibov) / Var(retorno_ibov). None
    sem retornos suficientes, ou se o Ibovespa não variou nada no período
    coberto (variância zero — divisão por zero)."""
    retornos_carteira, retornos_ibov, _ = _retornos_carteira_e_ibov(historico)
    if len(retornos_carteira) < MINIMO_RETORNOS_PARA_CALCULAR:
        return None
    media_carteira = _media(retornos_carteira)
    media_ibov = _media(retornos_ibov)
    var_ibov = _variancia_amostral(retornos_ibov, media_ibov)
    if var_ibov < _EPSILON_VARIANCIA:
        return None
    cov = _covariancia_amostral(retornos_carteira, retornos_ibov, media_carteira, media_ibov)
    return cov / var_ibov


def calcular_sharpe_anualizado(historico: list[dict[str, Any]], taxa_livre_risco_anual_pct: float) -> float | None:
    """
    Índice de Sharpe anualizado. Converte a taxa livre de risco informada
    (% ao ano — ex: a Selic/CDI do período) para "por período" usando o
    intervalo MÉDIO observado entre snapshots, e depois anualiza o
    resultado escalando por raiz(períodos por ano) — a convenção clássica
    de anualização de Sharpe, aqui aplicada de forma aproximada por causa
    da irregularidade dos snapshots (ver ressalva no topo do arquivo).

    None sem retornos suficientes, ou se a carteira não teve NENHUMA
    variação de retorno entre os períodos (desvio padrão zero).
    """
    retornos_carteira, _, dias_intervalos = _retornos_carteira_e_ibov(historico)
    if len(retornos_carteira) < MINIMO_RETORNOS_PARA_CALCULAR:
        return None

    dias_medios = _media([float(d) for d in dias_intervalos])
    if dias_medios <= 0:
        return None

    taxa_livre_risco_anual = taxa_livre_risco_anual_pct / 100
    taxa_livre_risco_periodo = (1 + taxa_livre_risco_anual) ** (dias_medios / 365.25) - 1

    media_retorno = _media(retornos_carteira)
    variancia = _variancia_amostral(retornos_carteira, media_retorno)
    if variancia < _EPSILON_VARIANCIA:
        return None
    desvio_padrao = variancia ** 0.5

    sharpe_periodo = (media_retorno - taxa_livre_risco_periodo) / desvio_padrao
    periodos_por_ano = 365.25 / dias_medios
    return sharpe_periodo * (periodos_por_ano ** 0.5)


def calcular_risco_carteira(historico: list[dict[str, Any]], taxa_livre_risco_anual_pct: float) -> ResultadoRisco:
    """Ponto de entrada único: junta beta + Sharpe + um aviso amigável
    quando não há dados suficientes ainda, pronto para exibir na tela."""
    retornos_carteira, _, dias_intervalos = _retornos_carteira_e_ibov(historico)
    numero_periodos = len(retornos_carteira)
    dias_cobertos = sum(dias_intervalos) if dias_intervalos else None

    if numero_periodos < MINIMO_RETORNOS_PARA_CALCULAR:
        return ResultadoRisco(
            beta=None,
            sharpe_anualizado=None,
            numero_periodos=numero_periodos,
            dias_cobertos=dias_cobertos,
            aviso=(
                f"Ainda faltam dados: {numero_periodos} período(s) disponível(is), "
                f"são necessários pelo menos {MINIMO_RETORNOS_PARA_CALCULAR}. Continue clicando em "
                '"🔄 Atualizar Dados" em dias diferentes para acumular histórico.'
            ),
        )

    return ResultadoRisco(
        beta=calcular_beta(historico),
        sharpe_anualizado=calcular_sharpe_anualizado(historico, taxa_livre_risco_anual_pct),
        numero_periodos=numero_periodos,
        dias_cobertos=dias_cobertos,
    )
