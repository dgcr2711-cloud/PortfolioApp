import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { cores, espacamento } from '../theme';

interface Props {
  rotulo: string;
  valor: string;
  corValor?: string;
  subvalor?: string;
  corSub?: string;
  destaque?: boolean;
}

/** Mesmo "card-kpi" do dashboard do PC — rótulo pequeno em cima, valor grande embaixo. */
export function CardKpi({ rotulo, valor, corValor = cores.texto, subvalor, corSub = cores.textoSecundario, destaque = false }: Props) {
  return (
    <View style={[estilos.card, destaque && estilos.cardDestaque]}>
      {destaque && <View style={estilos.barraDestaque} />}
      <Text style={estilos.rotulo}>{rotulo}</Text>
      <Text style={[estilos.valor, { color: corValor }]}>{valor}</Text>
      {subvalor ? <Text style={[estilos.subvalor, { color: corSub }]}>{subvalor}</Text> : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  card: {
    backgroundColor: cores.fundoCard,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.lg,
    flexBasis: '47%',
    flexGrow: 1,
    marginBottom: espacamento.md,
    overflow: 'hidden',
  },
  cardDestaque: {
    borderColor: 'rgba(212,175,55,0.45)',
  },
  barraDestaque: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 3,
    backgroundColor: cores.destaque,
  },
  rotulo: {
    fontSize: 11,
    fontWeight: '600',
    color: cores.textoSecundario,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  valor: {
    fontSize: 20,
    fontWeight: '700',
    marginTop: 4,
  },
  subvalor: {
    fontSize: 12,
    fontWeight: '500',
    marginTop: 2,
  },
});
