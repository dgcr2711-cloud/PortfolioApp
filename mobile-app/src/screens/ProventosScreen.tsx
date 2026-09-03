import React from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { BotaoOcultarValores } from '../components/BotaoOcultarValores';
import { useOcultarValores } from '../contexts/OcultarValoresContext';
import { cores, espacamento } from '../theme';
import { formatarData, formatarMoedaPriv, formatarPct } from '../format';
import type { Provento } from '../types';

/**
 * Espelha a aba 📅 Proventos do PC: resumo (total recebido, últimos 12
 * meses, Yield on Cost) + histórico completo. Só leitura — registrar um
 * provento continua sendo feito no PC, já que não é algo que costuma
 * precisar ser feito na hora, fora de casa.
 */
export function ProventosScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();
  const { ocultarValores } = useOcultarValores();

  if (carregando) {
    return (
      <View style={estilos.centralizado}>
        <ActivityIndicator color={cores.destaque} size="large" />
      </View>
    );
  }

  if (erro || !snapshot) {
    return (
      <View style={estilos.centralizado}>
        <Text style={estilos.textoErro}>{erro ?? 'Sem dados.'}</Text>
      </View>
    );
  }

  // Fallback pro formato antigo do snapshot (antes desta funcionalidade existir) — evita
  // tela quebrada enquanto o PC ainda não rodou "🔄 Atualizar Dados" com o código novo.
  const { resumo, lista } = snapshot.proventos ?? { resumo: { totalGeral: 0, total12m: 0, yieldOnCost: 0 }, lista: [] };

  return (
    <FlatList
      style={estilos.container}
      contentContainerStyle={estilos.lista}
      data={lista}
      keyExtractor={(item: Provento) => item.id}
      ListHeaderComponent={
        <>
          <View style={estilos.linhaTitulo}>
            <Text style={estilos.titulo}>Proventos</Text>
            <BotaoOcultarValores />
          </View>
          <Text style={estilos.legenda}>Dividendos, JCP e rendimentos — registrados manualmente no app do PC.</Text>

          <View style={estilos.blocoCards}>
            <Cartao rotulo="Total Recebido" valor={formatarMoedaPriv(resumo.totalGeral, ocultarValores)} />
            <Cartao rotulo="Últimos 12 meses" valor={formatarMoedaPriv(resumo.total12m, ocultarValores)} />
            <Cartao rotulo="Yield on Cost (12m)" valor={formatarPct(resumo.yieldOnCost)} destaque />
          </View>

          {lista.length > 0 && <Text style={estilos.subtitulo}>Histórico</Text>}
        </>
      }
      ListEmptyComponent={<Text style={estilos.aviso}>Nenhum provento registrado ainda.</Text>}
      renderItem={({ item }: { item: Provento }) => <LinhaProvento provento={item} ocultarValores={ocultarValores} />}
    />
  );
}

function Cartao({ rotulo, valor, destaque = false }: { rotulo: string; valor: string; destaque?: boolean }) {
  return (
    <View style={estilos.cartaoResumo}>
      <Text style={estilos.rotuloCartao}>{rotulo}</Text>
      <Text style={[estilos.valorCartao, destaque && { color: cores.destaque }]}>{valor}</Text>
    </View>
  );
}

function LinhaProvento({ provento, ocultarValores }: { provento: Provento; ocultarValores: boolean }) {
  return (
    <View style={estilos.linha}>
      <View>
        <Text style={estilos.ticker}>{provento.ticker}</Text>
        <Text style={estilos.tipoData}>{provento.tipo} · {formatarData(provento.data)}</Text>
      </View>
      <Text style={estilos.valor}>{formatarMoedaPriv(provento.valor, ocultarValores)}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14 },
  lista: { paddingHorizontal: espacamento.lg, paddingTop: espacamento.xl, paddingBottom: espacamento.xl },
  linhaTitulo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2, marginBottom: espacamento.lg, lineHeight: 17 },
  blocoCards: { flexDirection: 'row', gap: espacamento.sm, marginBottom: espacamento.lg },
  cartaoResumo: {
    flex: 1,
    backgroundColor: cores.fundoCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.sm,
  },
  rotuloCartao: { color: cores.textoApagado, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.2 },
  valorCartao: { color: cores.texto, fontSize: 15, fontWeight: '700', marginTop: 4 },
  subtitulo: { color: cores.destaque, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: espacamento.sm },
  aviso: { color: cores.neutro, fontSize: 13, lineHeight: 19 },
  linha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    marginBottom: espacamento.sm,
  },
  ticker: { color: cores.texto, fontWeight: '700', fontSize: 14 },
  tipoData: { color: cores.textoSecundario, fontSize: 11, marginTop: 2, textTransform: 'capitalize' },
  valor: { color: cores.positivo, fontWeight: '700', fontSize: 14 },
});
