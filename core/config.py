"""
Configurações e constantes globais do app.

Centralizar esses valores aqui facilita ajustes futuros: se um dia você
quiser mudar a margem de segurança padrão, o limite de isenção de IR, ou
onde o arquivo de dados fica salvo, é só mexer neste arquivo — nenhum
outro módulo precisa ser tocado.
"""

from pathlib import Path

# ----------------------------------------------------------------------
# Caminhos
# ----------------------------------------------------------------------
# Pasta raiz do projeto (onde este arquivo, subindo dois níveis, está).
PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = PASTA_RAIZ / "data"
ARQUIVO_DADOS = PASTA_DADOS / "portfolio_data.json"
PASTA_BACKUPS = PASTA_DADOS / "backups"

# Pasta FORA da pasta do projeto para guardar segredos (hoje só a chave do
# Firebase) — na pasta pessoal do usuário (equivalente a C:\Users\<você>\
# no Windows), nunca dentro de PortfolioApp. Motivo: se um dia a pasta do
# projeto for copiada, enviada a alguém ou colocada num repositório Git
# (ex: um backup no GitHub), nada aqui dentro vai junto — só o que estiver
# fora da pasta do projeto fica realmente protegido desse risco. Ver
# core/cloud_sync.py, que migra automaticamente uma chave antiga encontrada
# na raiz do projeto para cá, sem precisar de nenhuma ação manual.
PASTA_SEGREDOS = Path.home() / ".portfolio_b3_secrets"

# ----------------------------------------------------------------------
# Regras de negócio (mesmos valores usados no dashboard HTML original)
# ----------------------------------------------------------------------
MARGEM_SEGURANCA_PADRAO = 0.20          # 20% travado sobre o Preço Teto

# A Receita Federal já mudou a alíquota de IR sobre ações e o limite mensal
# de isenção no passado, e pode mudar de novo — para o app continuar
# calculando corretamente o IR de vendas ANTIGAS mesmo depois de uma
# mudança futura na regra, os dois valores ficam numa tabela por data de
# vigência, em vez de uma constante fixa única. Para registrar uma
# mudança, basta acrescentar uma nova linha no FIM desta lista com a data
# em que a nova regra passou a valer (formato "AAAA-MM-DD") — nenhuma
# fórmula em core/calculations.py ou core/imposto_renda.py precisa mudar.
# A lista deve ficar sempre ordenada por "vigente_desde" crescente; a
# primeira linha cobre "desde sempre" (qualquer venda antiga cai nela) até
# a data da próxima linha.
TABELA_IR_ACOES: list[dict] = [
    {"vigente_desde": "1900-01-01", "aliquota": 0.15, "limite_isencao_mensal": 20_000.0},
]


def regra_ir_vigente_em(data_iso: str | None, tabela: list[dict] | None = None) -> dict:
    """
    Devolve a linha de TABELA_IR_ACOES vigente numa data (aceita "AAAA-MM-DD"
    ou só "AAAA-MM" — a comparação de string funciona igual, por ser tudo
    formato ISO). Data vazia/None ou anterior à primeira linha cai na regra
    mais antiga cadastrada — nunca lança erro.

    O parâmetro `tabela` existe para os testes automatizados poderem
    simular uma mudança de alíquota/isenção sem mexer na tabela real; o uso
    normal (sem passar nada) sempre lê TABELA_IR_ACOES.

    Cuidado: comparar strings de tamanhos diferentes ("AAAA-MM" contra
    "AAAA-MM-DD") direto dá resultado errado bem no mês da mudança — ex:
    "2030-01" < "2030-01-01" na comparação lexicográfica normal de Python
    (string mais curta que é prefixo da mais longa conta como "menor"),
    então uma regra vigente desde "2030-01-01" pareceria só valer a partir
    de fevereiro. Por isso a comparação é sempre feita truncando as duas
    strings para o menor comprimento entre elas (equivalente a comparar só
    até a granularidade mais grossa informada).
    """
    tabela_efetiva = tabela if tabela is not None else TABELA_IR_ACOES
    aplicavel = tabela_efetiva[0]
    data_str = data_iso or ""
    if not data_str:
        # Sem essa saída antecipada, comparar "" (comprimento 0) contra
        # qualquer vigencia[:0] (também "") daria sempre True e o laço
        # abaixo terminaria pegando a regra mais NOVA, não a mais antiga.
        return aplicavel
    for linha in tabela_efetiva:
        vigencia = linha["vigente_desde"]
        comprimento = min(len(data_str), len(vigencia))
        if data_str[:comprimento] >= vigencia[:comprimento]:
            aplicavel = linha
        else:
            break
    return aplicavel


# Mantidos por compatibilidade com quem ainda importa os valores "soltos" —
# sempre iguais à regra mais recente da tabela acima. Código novo deve
# preferir regra_ir_vigente_em(data) para respeitar o histórico.
ALIQUOTA_IR_ACOES = TABELA_IR_ACOES[-1]["aliquota"]                # 15% sobre o lucro do mês, quando não isento
LIMITE_ISENCAO_IR_MENSAL = TABELA_IR_ACOES[-1]["limite_isencao_mensal"]  # Vendas de ações comuns até esse valor/mês são isentas de IR

WATCHLIST_PADRAO = ["ITUB4", "ALOS3", "ITSA4", "KLBN4"]

SETORES_PADRAO = [
    "Bancos", "Petróleo e Gás", "Mineração e Siderurgia", "Varejo",
    "Energia Elétrica/Saneamento", "Saúde", "Tecnologia", "Papel e Celulose",
    "Agronegócio", "Imobiliário", "Industrial", "Telecomunicações",
    "Educação", "Transporte e Logística", "Outros",
]

# Links de RI para consulta manual de releases (mesma lista do dashboard original)
LINKS_RI = {
    "PETR4": "https://www.investidorpetrobras.com.br/", "PETR3": "https://www.investidorpetrobras.com.br/",
    "VALE3": "https://vale.com/investors", "ITUB4": "https://www.itau.com.br/relacoes-com-investidores/",
    "BBDC4": "https://www.bradescori.com.br/", "BBAS3": "https://www.bb.com.br/ri",
    "WEGE3": "https://ri.weg.net/", "ABEV3": "https://ri.ambev.com.br/",
    "B3SA3": "https://ri.b3.com.br/", "MGLU3": "https://ri.magazineluiza.com.br/",
    "RENT3": "https://ri.localiza.com/", "SUZB3": "https://ri.suzano.com.br/",
    "RADL3": "https://ri.raiadrogasil.com.br/", "JBSS3": "https://ri.jbs.com.br/",
    "EQTL3": "https://ri.equatorialenergia.com.br/", "LREN3": "https://ri.lojasrenner.com.br/",
    "GGBR4": "https://ri.gerdau.com/", "CSAN3": "https://ri.cosan.com.br/",
    "PRIO3": "https://ri.prio3.com.br/", "HAPV3": "https://ri.hapvida.com.br/",
    "ALOS3": "https://ri.alliansce.com.br/", "ITSA4": "https://ri.itausa.com.br/",
    "KLBN4": "https://ri.klabin.com.br/",
}

# ----------------------------------------------------------------------
# Cotações (Yahoo Finance via yfinance)
# ----------------------------------------------------------------------
SUFIXO_B3 = ".SA"          # Ex: PETR4 -> PETR4.SA
TICKER_IBOVESPA = "^BVSP"

# TTL do cache "automático" (segundos). O botão "🔄 Atualizar Dados" ignora
# esse TTL e força uma busca nova imediatamente.
CACHE_TTL_COTACAO_SEGUNDOS = 5 * 60      # 5 minutos
CACHE_TTL_NOME_EMPRESA_SEGUNDOS = 24 * 60 * 60  # 24h (nome da empresa não muda)
CACHE_TTL_FUNDAMENTOS_SEGUNDOS = 24 * 60 * 60   # 24h — P/L, ROE etc. não mudam intradia

# ----------------------------------------------------------------------
# Análise de carteira (concentração, diversificação)
# ----------------------------------------------------------------------
# Regra clássica de gestão de risco: um único ativo acima disso do
# patrimônio dispara um alerta de concentração na Visão Geral.
LIMITE_CONCENTRACAO_ALERTA_PCT = 20.0

# ----------------------------------------------------------------------
# Cores (mesma paleta do dashboard original — Tailwind "emerald/rose/sky" —
# mais um tom "dourado" para destacar leituras de qualidade/valuation no
# painel de diagnóstico, inspirado na estética sóbria de relatórios de
# investimento institucionais)
# ----------------------------------------------------------------------
COR_POSITIVO = "#34d399"   # emerald-400
COR_NEGATIVO = "#fb7185"   # rose-400
COR_NEUTRO = "#9ca3af"     # gray-400
COR_INFO = "#38bdf8"       # sky-400
COR_DESTAQUE = "#d4af37"   # dourado — usado com moderação, só em leituras-chave
COR_FUNDO_CARD = "#1f2937"  # gray-800
COR_FUNDO_APP = "#111827"   # gray-900
