/**
 * Mesma paleta de cores do app do PC (core/config.py), pra manter os dois
 * apps com a mesma identidade visual — fundo escuro, dourado como cor de
 * destaque só nas leituras mais importantes de value investing.
 *
 * 2026-09-04 (Diego pediu pra atualizar o celular "com as mesmas
 * características" do PC): o PC ganhou o tema "Executivo Black" numa
 * rodada anterior (fundo/cards mais escuros e neutros, texto num tom
 * levemente suave em vez de branco puro — ver core/config.py) mas o
 * celular tinha ficado pra trás, ainda na paleta azulada antiga. Valores
 * abaixo atualizados pra baterem exatamente com as constantes COR_* de
 * core/config.py — `borda` e `textoApagado` já batiam por coincidência,
 * não mudaram.
 */
export const cores = {
  positivo: '#34d399',       // COR_POSITIVO
  negativo: '#F87171',       // COR_NEGATIVO (era '#fb7185')
  neutro: '#9ca3af',         // COR_NEUTRO
  info: '#38bdf8',           // COR_INFO
  destaque: '#d4af37',       // COR_DESTAQUE — dourado, usado com moderação
  fundoApp: '#252324',       // COR_FUNDO_APP "Executivo Black" (era '#111827')
  fundoCard: '#1E1C1D',      // COR_FUNDO_CARD "Executivo Black" (era '#1f2937')
  borda: '#313d4f',
  texto: '#F4F4F5',          // COR_TEXTO_PRIMARIO (era '#ffffff', branco puro)
  textoSecundario: '#A1A1AA', // COR_TEXTO_SECUNDARIO (era '#9ca3af', igual a "neutro")
  textoApagado: '#6b7280',
};

export const espacamento = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
};
