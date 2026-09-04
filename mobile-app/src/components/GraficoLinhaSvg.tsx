import React, { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop } from 'react-native-svg';
import { cores, espacamento } from '../theme';

// Mesmo motivo do cast em GraficoDonutAlocacao.tsx: o stub/tipagem de
// react-native-svg usado neste projeto não aceita todas as props reais dos
// componentes sem reclamar — cast pra `any` evita ficar lutando com isso
// num componente que só desenha SVG simples.
const SvgC = Svg as unknown as React.ComponentType<any>;
const PathC = Path as unknown as React.ComponentType<any>;
const LineC = Line as unknown as React.ComponentType<any>;
const CircleC = Circle as unknown as React.ComponentType<any>;
const DefsC = Defs as unknown as React.ComponentType<any>;
const LinearGradientC = LinearGradient as unknown as React.ComponentType<any>;
const StopC = Stop as unknown as React.ComponentType<any>;

export interface SerieGrafico {
  valores: (number | null)[]; // mesmo comprimento de `rotulosX`; null = sem dado nesse ponto
  cor: string;
  preencher?: boolean; // sombra em degradê abaixo da linha (pensado pra série principal)
  tracejada?: boolean;
}

interface Props {
  series: SerieGrafico[];
  rotulosX: string[]; // mesmo comprimento de `valores` de cada série — só mostramos alguns (extremos)
  altura?: number;
  linhaReferencia?: { valor: number; cor: string; rotulo: string };
  formatarValor?: (v: number) => string;
  // Margem de "respiro" acima/abaixo do mínimo/máximo real dos dados — mesma
  // ideia de ui/graficos.py::_intervalo_eixo_y (0.08 lá pro patrimônio, 0.12
  // pro preço de um ativo só, que varia numa faixa mais estreita).
  margemPct?: number;
}

/**
 * Gráfico de linha em SVG (react-native-svg, já usado em
 * GraficoDonutAlocacao.tsx) — reaproveitado tanto na Evolução Patrimonial
 * quanto no gráfico de preço por ativo da aba Preço Teto.
 *
 * 2026-09-04 (Diego reportou "o gráfico [de Evolução] está muito ruim,
 * fazer um semelhante ao do site"): substitui o gráfico anterior
 * (`GraficoLinhaPatrimonio`, feito só com `<View>` giradas — sem
 * react-native-svg) por um de verdade, no mesmo espírito visual do
 * gráfico do site (`ui/graficos.py`): linha limpa + sombra em degradê
 * sob a série principal (equivalente ao `fill="tonexty"` do Plotly),
 * range do eixo Y com respiro em vez de partir de zero sempre, rótulos
 * de data compactos ("MM/AA", só nas pontas) e um ponto de destaque no
 * último valor da série principal.
 */
export function GraficoLinhaSvg({
  series,
  rotulosX,
  altura = 160,
  linhaReferencia,
  formatarValor,
  margemPct = 0.08,
}: Props) {
  const [largura, setLargura] = useState(0);

  const todosValores = series.flatMap((s) => s.valores).filter((v): v is number => v !== null && Number.isFinite(v));
  if (todosValores.length < 2 || rotulosX.length < 2) {
    return <Text style={estilos.aviso}>Dados insuficientes para desenhar o gráfico.</Text>;
  }

  const valoresParaRange = linhaReferencia ? [...todosValores, linhaReferencia.valor] : todosValores;
  const minimo = Math.min(...valoresParaRange);
  const maximo = Math.max(...valoresParaRange);
  const respiro = minimo === maximo ? (Math.abs(minimo) * margemPct || 1) : (maximo - minimo) * margemPct;
  // Valores financeiros aqui (patrimônio, preço de ativo) nunca são negativos
  // — o piso em 0 evita respiro inútil abaixo de zero (mesma regra do site).
  const rangeMin = Math.max(0, minimo - respiro);
  const rangeMax = maximo + respiro;
  const amplitude = Math.max(1e-9, rangeMax - rangeMin);

  const n = rotulosX.length;
  function paraX(i: number): number {
    return (i / (n - 1)) * largura;
  }
  function paraY(valor: number): number {
    return altura - ((valor - rangeMin) / amplitude) * altura;
  }

  function caminhoDaSerie(valores: (number | null)[]): string {
    let d = '';
    let comecou = false;
    valores.forEach((v, i) => {
      if (v === null || !Number.isFinite(v)) return;
      const comando = comecou ? 'L' : 'M';
      d += `${comando}${paraX(i).toFixed(1)},${paraY(v).toFixed(1)} `;
      comecou = true;
    });
    return d.trim();
  }

  function caminhoDaArea(valores: (number | null)[]): string {
    const linha = caminhoDaSerie(valores);
    if (!linha) return '';
    const indicesComValor = valores.map((v, i) => (v !== null && Number.isFinite(v) ? i : null)).filter((i): i is number => i !== null);
    const primeiro = indicesComValor[0];
    const ultimo = indicesComValor[indicesComValor.length - 1];
    return `${linha} L${paraX(ultimo).toFixed(1)},${altura} L${paraX(primeiro).toFixed(1)},${altura} Z`;
  }

  const serieComReferenciaParaUltimoPonto = series.find((s) => s.preencher) ?? series[0];
  const valoresPrincipais = serieComReferenciaParaUltimoPonto.valores;
  const ultimoIndiceComValor = [...valoresPrincipais].reverse().findIndex((v) => v !== null && Number.isFinite(v));
  const indiceUltimoPonto = ultimoIndiceComValor === -1 ? -1 : valoresPrincipais.length - 1 - ultimoIndiceComValor;

  return (
    <View>
      <View style={[estilos.area, { height: altura }]} onLayout={(e: { nativeEvent: { layout: { width: number } } }) => setLargura(e.nativeEvent.layout.width)}>
        {largura > 0 && (
          <SvgC width={largura} height={altura}>
            <DefsC>
              {series.filter((s) => s.preencher).map((s, i) => (
                <LinearGradientC key={`grad-${i}`} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                  <StopC offset="0" stopColor={s.cor} stopOpacity={0.22} />
                  <StopC offset="1" stopColor={s.cor} stopOpacity={0} />
                </LinearGradientC>
              ))}
            </DefsC>

            {linhaReferencia && (
              <LineC
                x1={0} x2={largura}
                y1={paraY(linhaReferencia.valor)} y2={paraY(linhaReferencia.valor)}
                stroke={linhaReferencia.cor} strokeWidth={1.5} strokeDasharray="5,4"
              />
            )}

            {series.map((s, i) =>
              s.preencher ? (
                <PathC key={`area-${i}`} d={caminhoDaArea(s.valores)} fill={`url(#grad-${i})`} stroke="none" />
              ) : null
            )}
            {series.map((s, i) => (
              <PathC
                key={`linha-${i}`}
                d={caminhoDaSerie(s.valores)}
                stroke={s.cor}
                strokeWidth={2}
                strokeDasharray={s.tracejada ? '5,4' : undefined}
                fill="none"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ))}

            {indiceUltimoPonto >= 0 && valoresPrincipais[indiceUltimoPonto] !== null && (
              <CircleC
                cx={paraX(indiceUltimoPonto)}
                cy={paraY(valoresPrincipais[indiceUltimoPonto] as number)}
                r={4}
                fill={serieComReferenciaParaUltimoPonto.cor}
              />
            )}
          </SvgC>
        )}

        {linhaReferencia && largura > 0 && (
          <Text
            style={[estilos.rotuloReferencia, { color: linhaReferencia.cor, top: Math.max(2, paraY(linhaReferencia.valor) - 14) }]}
            numberOfLines={1}
          >
            {linhaReferencia.rotulo}
          </Text>
        )}
        {formatarValor && (
          <Text style={estilos.rotuloTopo}>{formatarValor(rangeMax)}</Text>
        )}
      </View>
      <View style={estilos.linhaEixoX}>
        <Text style={estilos.rotuloEixoX}>{rotulosX[0]}</Text>
        <Text style={estilos.rotuloEixoX}>{rotulosX[rotulosX.length - 1]}</Text>
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  aviso: { color: cores.neutro, fontSize: 13, lineHeight: 19 },
  area: {
    position: 'relative',
    backgroundColor: cores.fundoCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: cores.borda,
    overflow: 'hidden',
    marginTop: espacamento.xs,
  },
  rotuloTopo: { position: 'absolute', top: 4, left: 6, color: cores.textoApagado, fontSize: 10 },
  rotuloReferencia: { position: 'absolute', right: 6, fontSize: 10, fontWeight: '700' },
  linhaEixoX: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4, marginBottom: espacamento.sm },
  rotuloEixoX: { color: cores.textoApagado, fontSize: 10 },
});
