/**
 * Formatação no padrão brasileiro (R$ 1.234,56 / 12,34%) — mesma lógica de
 * core/formatting.py, reescrita em TypeScript porque o celular não roda
 * Python. Se um dia isso incomodar por estar "duplicado", a alternativa
 * seria expor esses valores já formatados no snapshot; optei por manter o
 * celular formatando os números brutos porque dá mais liberdade de layout
 * (ex: quebrar em duas linhas, mudar casas decimais) sem precisar mudar o
 * lado Python.
 */

export function formatarMoeda(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return 'R$ —';
  const negativo = valor < 0;
  const absoluto = Math.abs(valor);
  const texto = absoluto.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${negativo ? '-' : ''}R$ ${texto}`;
}

/**
 * Igual a formatarMoeda, mas mascara o valor quando o "modo privacidade"
 * (ocultar valores) está ativo — mesma lógica de core/formatting.py's
 * formatar_moeda_priv().
 */
export function formatarMoedaPriv(valor: number | null | undefined, ocultar: boolean): string {
  return ocultar ? 'R$ ••••••' : formatarMoeda(valor);
}

/** Mascara uma quantidade de ações quando o "modo privacidade" está ativo — mesma lógica de core/formatting.py's mascarar_qtd(). */
export function mascararQtd(qtd: number | null | undefined, ocultar: boolean): string {
  if (ocultar) return '•••';
  if (qtd === null || qtd === undefined || !Number.isFinite(qtd)) return '—';
  return Number.isInteger(qtd) ? String(qtd) : formatarNumero(qtd, 4);
}

export function formatarPct(valor: number | null | undefined, casas = 2): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '—';
  return `${valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })}%`;
}

export function formatarNumero(valor: number | null | undefined, casas = 2): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '—';
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function formatarData(dataIso: string | null | undefined): string {
  if (!dataIso || dataIso.length < 10) return '—';
  const [ano, mes, dia] = dataIso.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

export function formatarDataHora(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  const data = new Date(isoString);
  if (Number.isNaN(data.getTime())) return '—';
  return data.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}
