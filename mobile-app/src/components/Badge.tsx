import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { cores } from '../theme';
import type { Indicacao } from '../types';

type TipoBadge = 'ok' | 'warn' | 'neutral' | 'info' | 'destaque';

const CORES_POR_TIPO: Record<TipoBadge, { fundo: string; texto: string; borda: string }> = {
  ok: { fundo: 'rgba(16,185,129,0.15)', texto: cores.positivo, borda: 'rgba(16,185,129,0.4)' },
  warn: { fundo: 'rgba(244,63,94,0.15)', texto: cores.negativo, borda: 'rgba(244,63,94,0.4)' },
  neutral: { fundo: 'rgba(156,163,175,0.12)', texto: cores.neutro, borda: 'rgba(156,163,175,0.3)' },
  info: { fundo: 'rgba(56,189,248,0.15)', texto: cores.info, borda: 'rgba(56,189,248,0.4)' },
  destaque: { fundo: 'rgba(212,175,55,0.14)', texto: cores.destaque, borda: 'rgba(212,175,55,0.4)' },
};

export function Badge({ texto, tipo }: { texto: string; tipo: TipoBadge }) {
  const paleta = CORES_POR_TIPO[tipo];
  return (
    <View style={[estilos.badge, { backgroundColor: paleta.fundo, borderColor: paleta.borda }]}>
      <Text style={[estilos.texto, { color: paleta.texto }]}>{texto}</Text>
    </View>
  );
}

/** Badge de Indicação (🟢 Compra / 🟡 Neutro / 🔴 Venda) — mesma regra do app do PC. */
export function BadgeIndicacao({ indicacao }: { indicacao: Indicacao }) {
  if (!indicacao) return <Text style={estilos.textoApagado}>— sem dados</Text>;
  const mapa: Record<NonNullable<Indicacao>, { texto: string; tipo: TipoBadge }> = {
    compra: { texto: '🟢 Compra', tipo: 'ok' },
    neutro: { texto: '🟡 Neutro', tipo: 'neutral' },
    venda: { texto: '🔴 Venda', tipo: 'warn' },
  };
  const { texto, tipo } = mapa[indicacao];
  return <Badge texto={texto} tipo={tipo} />;
}

const estilos = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    borderWidth: 1,
  },
  texto: {
    fontSize: 11,
    fontWeight: '600',
  },
  textoApagado: {
    color: cores.textoApagado,
    fontSize: 12,
  },
});
