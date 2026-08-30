import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { cores, espacamento } from '../theme';
import { formatarPct } from '../format';

/**
 * Mesma paleta de cores do gráfico de alocação do PC
 * (ui/carteira.py::PALETA_ALOCACAO), pra manter a mesma identidade visual
 * entre as duas plataformas.
 */
const PALETA_ALOCACAO = [
  '#34d399', '#38bdf8', '#fbbf24', '#a78bfa', '#fb7185',
  '#22d3ee', '#f472b6', '#a3e635', '#fb923c', '#94a3b8',
];

export interface FatiaAlocacao {
  rotulo: string;
  valor: number;
}

/**
 * Espelha o gráfico de "Alocação" da aba 📈 Carteira do PC — lá é um donut
 * feito com plotly (biblioteca de gráficos em Python). O celular não tem
 * uma biblioteca de gráficos instalada (o projeto evita adicionar
 * dependências novas ao app do celular, já que o registro do npm fica
 * bloqueado no ambiente onde o código é verificado, e uma dependência
 * nativa quebrada é difícil de depurar remotamente). Em vez disso, a MESMA
 * informação — quanto cada ativo/setor pesa na carteira — é mostrada como
 * uma barra segmentada + legenda com percentuais, sem depender de nada
 * além do React Native puro.
 */
export function GraficoAlocacao({ dados }: { dados: FatiaAlocacao[] }) {
  const total = dados.reduce((soma, item) => soma + item.valor, 0);

  if (dados.length === 0 || total <= 0) {
    return <Text style={estilos.vazio}>Sem posições para exibir no gráfico ainda.</Text>;
  }

  const ordenados = [...dados].sort((a, b) => b.valor - a.valor);

  return (
    <View>
      <View style={estilos.barra}>
        {ordenados.map((item, indice) => (
          <View
            key={item.rotulo}
            style={{ flex: item.valor, backgroundColor: PALETA_ALOCACAO[indice % PALETA_ALOCACAO.length] }}
          />
        ))}
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
  barra: {
    flexDirection: 'row',
    height: 14,
    borderRadius: 7,
    overflow: 'hidden',
    backgroundColor: cores.borda,
  },
  legenda: { marginTop: espacamento.md, gap: 7 },
  linhaLegenda: { flexDirection: 'row', alignItems: 'center', gap: espacamento.sm },
  marcador: { width: 10, height: 10, borderRadius: 5 },
  rotuloLegenda: { color: '#c3cad6', fontSize: 12, flex: 1 },
  valorLegenda: { color: cores.texto, fontSize: 12, fontWeight: '700' },
});
