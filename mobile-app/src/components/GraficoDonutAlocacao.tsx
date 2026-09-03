import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { cores, espacamento } from '../theme';
import { formatarPct } from '../format';
import { PALETA_ALOCACAO } from './GraficoAlocacao';
import type { FatiaAlocacao } from './GraficoAlocacao';

/**
 * Gráfico de alocação em forma de rosca (donut) de verdade — pedido por
 * Diego (2026-09-03), no estilo do gráfico do TradeMap. Desenhado com
 * react-native-svg (única dependência nova do app do celular, oficialmente
 * mantida pela Software Mansion e já compatível com a versão do Expo deste
 * projeto — ver package.json), empilhando um arco colorido por fatia sobre
 * um círculo (technique clássica: strokeDasharray + strokeDashoffset em
 * cima de um <Circle> sem preenchimento, "cortado" em pedaços).
 *
 * Substitui, na tela de Visão Geral, a barra segmentada de
 * GraficoAlocacao.tsx (mantida à parte, sem dependências, como alternativa
 * — ver o comentário lá).
 */

const RAIO = 62;
const GROSSURA = 20;
const CIRCUNFERENCIA = 2 * Math.PI * RAIO;
const TAMANHO_SVG = (RAIO + GROSSURA) * 2;
const CENTRO = TAMANHO_SVG / 2;

export function GraficoDonutAlocacao({
  dados,
  rotuloCentral,
  valorCentral,
}: {
  dados: FatiaAlocacao[];
  rotuloCentral?: string;
  valorCentral?: string;
}) {
  const total = dados.reduce((soma, item) => soma + item.valor, 0);

  if (dados.length === 0 || total <= 0) {
    return <Text style={estilos.vazio}>Sem posições para exibir no gráfico ainda.</Text>;
  }

  const ordenados = [...dados].sort((a, b) => b.valor - a.valor);

  let acumulado = 0;
  const fatias = ordenados.map((item, indice) => {
    const fracao = item.valor / total;
    const comprimentoArco = fracao * CIRCUNFERENCIA;
    // Um pequeno "gap" entre fatias (2px) deixa o donut mais legível quando
    // há várias posições pequenas — sem gap ficaria tudo colado.
    const gap = dados.length > 1 ? 2 : 0;
    const arco = Math.max(comprimentoArco - gap, 0);
    const dashArray = `${arco} ${CIRCUNFERENCIA - arco}`;
    const dashOffset = -acumulado;
    acumulado += comprimentoArco;
    return (
      <Circle
        key={item.rotulo}
        cx={CENTRO}
        cy={CENTRO}
        r={RAIO}
        stroke={PALETA_ALOCACAO[indice % PALETA_ALOCACAO.length]}
        strokeWidth={GROSSURA}
        strokeDasharray={dashArray}
        strokeDashoffset={dashOffset}
        strokeLinecap="butt"
        fill="transparent"
      />
    );
  });

  return (
    <View>
      <View style={estilos.areaDonut}>
        <Svg width={TAMANHO_SVG} height={TAMANHO_SVG} style={estilos.rotacaoInicial}>
          {/* Trilha de fundo (mostra o círculo completo antes das fatias coloridas) */}
          <Circle cx={CENTRO} cy={CENTRO} r={RAIO} stroke={cores.borda} strokeWidth={GROSSURA} fill="transparent" />
          {fatias}
        </Svg>
        {(rotuloCentral || valorCentral) && (
          <View style={estilos.centroTexto} pointerEvents="none">
            {valorCentral && (
              <Text style={estilos.valorCentral} numberOfLines={1} adjustsFontSizeToFit>
                {valorCentral}
              </Text>
            )}
            {rotuloCentral && <Text style={estilos.rotuloCentral}>{rotuloCentral}</Text>}
          </View>
        )}
      </View>
      <View style={estilos.legenda}>
        {ordenados.map((item, indice) => (
          <View key={item.rotulo} style={estilos.linhaLegenda}>
            <View style={[estilos.marcador, { backgroundColor: PALETA_ALOCACAO[indice % PALETA_ALOCACAO.length] }]} />
            <Text style={estilos.rotuloLegenda} numberOfLines={1}>
              {item.rotulo}
            </Text>
            <Text style={estilos.valorLegenda}>{formatarPct((item.valor / total) * 100)}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  vazio: { color: cores.textoApagado, fontSize: 12, marginTop: espacamento.xs },
  areaDonut: {
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: espacamento.xs,
  },
  // O <Circle> do SVG começa a desenhar às 3 horas (ângulo 0) — girar o SVG
  // inteiro -90° faz a primeira fatia começar no topo (12 horas), como
  // qualquer donut/pizza chart costuma ser desenhado.
  rotacaoInicial: { transform: [{ rotate: '-90deg' }] },
  centroTexto: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  valorCentral: { color: cores.texto, fontSize: 15, fontWeight: '700', maxWidth: RAIO * 1.5, textAlign: 'center' },
  rotuloCentral: { color: cores.textoApagado, fontSize: 10, marginTop: 2 },
  legenda: { marginTop: espacamento.md, gap: 7 },
  linhaLegenda: { flexDirection: 'row', alignItems: 'center', gap: espacamento.sm },
  marcador: { width: 10, height: 10, borderRadius: 5 },
  rotuloLegenda: { color: '#c3cad6', fontSize: 12, flex: 1 },
  valorLegenda: { color: cores.texto, fontSize: 12, fontWeight: '700' },
});
