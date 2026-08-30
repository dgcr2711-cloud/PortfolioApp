/**
 * Espelha exatamente o formato do snapshot montado em
 * core/mobile_snapshot.py (lado Python) — se um campo mudar lá, mude aqui
 * também. Manter os dois em sincronia manualmente é o preço de não ter um
 * gerador automático de tipos; para um projeto deste tamanho, compensa a
 * simplicidade de não introduzir mais uma ferramenta.
 */

export type Indicacao = 'compra' | 'neutro' | 'venda' | null;

export interface Totais {
  totalAtual: number;
  totalInvestido: number;
  lucro: number;
  rentabilidadePct: number;
  variacaoDiaReais: number;
  proventos12m: number;
}

export interface FundamentosAtivo {
  setorYahoo: string | null;
  pl: number | null;
  plProjetado: number | null;
  pvp: number | null;
  // LPA (lucro por ação) e VPA (valor patrimonial por ação) — usados pelo
  // "football field" de valuation (Número de Graham e Valor Patrimonial).
  // Ausentes em snapshots antigos (de antes desta funcionalidade).
  lpa?: number | null;
  vpa?: number | null;
  dividendYield: number | null;
  payoutRatio: number | null;
  payoutTtmCalculado: number | null;
  roe: number | null;
  margemLiquida: number | null;
  dividaPatrimonio: number | null;
  valorMercado: number | null;
  // Mesmos indicadores da tabela "🎯 Indicadores para o Preço Teto" do PC.
  freeCashflow: number | null;
  dividaLiquida: number | null;
  numAcoes: number | null;
  crescimentoReceita: number | null;
  beta: number | null;
  minima52s: number | null;
  maxima52s: number | null;
}

export interface CriterioPiotroski {
  chave: string;
  rotulo: string;
  grupo: string;
  passou: boolean | null;
}

export interface ResultadoPiotroski {
  pontos: number;
  totalAvaliado: number;
  classificacao: string;
  criterios: CriterioPiotroski[];
}

export interface ResultadoAltman {
  zScore: number | null;
  classificacao: string;
}

export interface MetodoValuation {
  nome: string;
  precoJusto: number;
}

export interface FootballField {
  metodos: MetodoValuation[];
  minimo: number;
  maximo: number;
  media: number;
}

export interface Ativo {
  ticker: string;
  ehAlvo: boolean;
  setor: string | null;
  qtdTotal: number | null;
  precoMedio: number | null;
  cotacaoAtual: number | null;
  atual: number | null;
  lucroReais: number | null;
  lucroPct: number | null;
  variacaoDiaPct: number | null;
  precoTeto: number | null;
  indicacao: Indicacao;
  fundamentos: FundamentosAtivo | null;
  // Análise avançada (core/piotroski.py, core/altman.py,
  // core/valuation_multiplos.py) — ausentes em snapshots antigos (de antes
  // desta funcionalidade) e None enquanto o PC não buscar/tiver dado
  // suficiente pra calcular.
  piotroski?: ResultadoPiotroski | null;
  altman?: ResultadoAltman | null;
  footballField?: FootballField | null;
}

export interface DiversificacaoSetor {
  setor: string;
  valor: number;
  peso_pct: number;
}

export interface FundamentosPonderados {
  pl: number | null;
  pvp: number | null;
  dividend_yield: number | null;
  roe: number | null;
  cobertura_pct: number;
}

export interface Diagnostico {
  maiorTicker: string | null;
  maiorPesoPct: number;
  indiceHhi: number;
  classificacaoHhi: 'baixa' | 'moderada' | 'alta';
  alertaConcentracao: boolean;
  setores: DiversificacaoSetor[];
  cagrAproximado: number | null;
  maiorPerdaRegistrada: number | null;
  fundamentosPonderados: FundamentosPonderados;
}

export interface PontoHistorico {
  data: string;
  totalInvestido: number;
  totalAtual: number;
  ibov: number | null;
}

export interface TwrVsIbovespa {
  rentCarteiraPct: number;
  rentIbovPct: number;
  dataInicio: string;
  dataFim: string;
}

/**
 * Beta e Índice de Sharpe aproximados da carteira (core/risco.py) — mesma
 * fonte de dados do histórico acima (dados["historico"]), calculados com a
 * taxa livre de risco que o usuário configurou na aba Evolução do PC.
 * beta/sharpeAnualizado vêm null quando ainda não há snapshots suficientes
 * (ver 'aviso' nesse caso) ou quando a variância no período é zero.
 */
export interface Risco {
  beta: number | null;
  sharpeAnualizado: number | null;
  numeroPeriodos: number;
  diasCobertos: number | null;
  aviso: string | null;
  taxaLivreRiscoAnualPctUsada: number;
}

/**
 * Desvio entre a meta de alocação (%) definida no PC e o peso atual de um
 * ativo (core/rebalanceamento.py) — só existe para tickers com meta
 * definida. O celular apenas EXIBE; quem define as metas é a aba Carteira
 * do PC.
 */
export interface DesvioAlocacao {
  ticker: string;
  metaPct: number;
  atualPct: number;
  desvioPp: number;      // atualPct - metaPct: positivo = acima da meta (venderia), negativo = abaixo (compraria)
  valorAtual: number;
  valorAlvo: number;
  valorAjuste: number;   // positivo = sugestão de compra, negativo = sugestão de venda
  alerta: boolean;
}

export interface Rebalanceamento {
  temMetas: boolean;
  desvios: DesvioAlocacao[];
}

export interface Provento {
  id: string;
  ticker: string;
  data: string;
  tipo: string;
  valor: number;
}

export interface ResumoProventos {
  totalGeral: number;
  total12m: number;
  yieldOnCost: number;
}

export interface Proventos {
  resumo: ResumoProventos;
  lista: Provento[];
}

export interface PrecoTeto {
  ticker: string;
  precoTeto: number;
  precoTetoComMargem: number;
  atualizadoEm: string | null;
}

export interface Transacao {
  id: string;
  tipo: 'compra' | 'venda';
  ticker: string;
  data: string;
  qtd: number;
  preco: number;
  taxas: number;
}

export interface ResumoMensalIR {
  mes: string;
  swingVendido: number;
  swingLucro: number;
  swingIsento: boolean;
  swingImposto: number;
  swingIrrf: number;
  dayTradeLucro: number;
  dayTradeImposto: number;
  dayTradeIrrf: number;
  impostoDevidoMes: number;
  darfAPagar: number;
  abaixoDoMinimo: boolean;
}

export interface PosicaoBens {
  ticker: string;
  qtdTotal: number;
  valorTotalInvestido: number;
  precoMedioPonderado: number;
}

export interface BensEDireitosAno {
  ano: string;
  dataCorte: string;
  posicoes: PosicaoBens[];
  totalInvestido: number;
}

export interface ProventosAno {
  ano: string;
  dividendos: number;
  jcp: number;
  rendimentosFii: number;
  jcpIrrfEstimado: number;
}

export interface ImpostoRenda {
  resumoMensal: ResumoMensalIR[];
  bensEDireitos: BensEDireitosAno[];
  proventosPorAno: ProventosAno[];
  avisos: string[];
}

export interface EntradaTese {
  id: string;
  data: string;
  texto: string;
}

export interface PortfolioSnapshot {
  atualizadoEm: string;
  totais: Totais;
  ativos: Ativo[];
  diagnostico: Diagnostico;
  historico: PontoHistorico[];
  twrVsIbovespa: TwrVsIbovespa | null;
  /** Ausente em snapshots antigos (de antes desta funcionalidade). */
  risco?: Risco | null;
  /** Ausente em snapshots antigos (de antes desta funcionalidade). */
  rebalanceamento?: Rebalanceamento | null;
  proventos: Proventos;
  precosTeto: PrecoTeto[];
  compras: Transacao[];
  impostoRenda: ImpostoRenda;
  /** Ticker -> entradas do Diário de Tese, mais recente primeiro. Ausente em snapshots antigos (de antes desta funcionalidade). */
  teses?: Record<string, EntradaTese[]>;
}
