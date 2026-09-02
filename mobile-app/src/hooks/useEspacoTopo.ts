import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { espacamento } from '../theme';

/**
 * Espaço seguro pro topo de uma tela (evita o título/conteúdo ficar
 * embaixo do relógio/bateria/notch do celular) + um respiro visual por
 * cima, do jeito que o resto do app já usa (espacamento.*).
 *
 * Antes disso (até 2026-09-01), cada tela usava um `paddingTop` fixo
 * (`espacamento.xl`, só 24px) — funcionava por sorte em alguns aparelhos,
 * mas não é suficiente pra cobrir a "área segura" de verdade em celulares
 * com notch/Dynamic Island/status bar mais alta, e por isso o conteúdo
 * aparecia colado (ou embaixo) da área do relógio/bateria do celular.
 * `useSafeAreaInsets()` (react-native-safe-area-context, já era uma
 * dependência do projeto, só não estava sendo usada em lugar nenhum) dá o
 * tamanho exato dessa área pra CADA aparelho, então isso passa a se
 * ajustar sozinho em qualquer celular.
 */
export function useEspacoTopo(respiroExtra: number = espacamento.lg): number {
  const insets = useSafeAreaInsets();
  return insets.top + respiroExtra;
}
