import React from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { BotaoOcultarValores } from '../components/BotaoOcultarValores';
import { useOcultarValores } from '../contexts/OcultarValoresContext';
import { cores, espacamento } from '../theme';
import { formatarMoeda, formatarMoedaPriv, formatarNumero } from '../format';
import type { BensEDireitosAno, ImpostoRenda, ProventosAno, ResumoMensalIR } from '../types';

const IMPOSTO_RENDA_VAZIO: ImpostoRenda = { resumoMensal: [], bensEDireitos: [], proventosPorAno: [], avisos: [] };

/**
 * Espelha a aba 🏛️ Imposto de Renda do PC (só a parte interativa — o
 * estudo completo, com todas as explicações de regras, fica no PC, que
 * tem mais espaço de tela). Aqui: resumo mensal Swing x Day Trade (já
 * compensando prejuízo e descontando IRRF), posição de anos fechados pra
 * "Bens e Direitos" e totais de proventos por ano — tudo pré-calculado
 * pelo PC (core/imposto_renda.py via mobile_snapshot.py), o celular só
 * formata e mostra. Só leitura, igual Proventos e Evolução.
 */
export function ImpostoRendaScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();

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
  const { resumoMensal, bensEDireitos, proventosPorAno, avisos } = snapshot.impostoRenda ?? IMPOSTO_RENDA_VAZIO;
  const mesesRecentesPrimeiro = [...(resumoMensal ?? [])].reverse();

  return (
    <FlatList
      style={estilos.container}
      contentContainerStyle={estilos.lista}
      data={mesesRecentesPrimeiro}
      keyExtractor={(item) => item.mes}
      ListHeaderComponent={
        <>
          <View style={estilos.linhaTitulo}>
            <Text style={estilos.titulo}>Imposto de Renda</Text>
            <BotaoOcultarValores />
          </View>
          <Text style={estilos.legenda}>
            Estimativas calculadas a partir das suas compras e vendas. Não substitui o Informe de
            Rendimentos da corretora nem a conferência com um contador.
          </Text>

          {(avisos ?? []).map((aviso, i) => (
            <View key={i} style={estilos.cartaoAviso}>
              <Text style={estilos.textoAviso}>⚠️ {aviso}</Text>
            </View>
          ))}

          {mesesRecentesPrimeiro.length > 0 && <Text style={estilos.subtitulo}>Resumo Mensal</Text>}
        </>
      }
      ListEmptyComponent={
        <Text style={estilos.aviso}>Nenhuma venda registrada ainda — assim que houver uma, o resumo aparece aqui.</Text>
      }
      renderItem={({ item }) => <CartaoMes item={item} />}
      ListFooterComponent={
        <>
          <SecaoBensEDireitos anos={bensEDireitos ?? []} />
          <SecaoProventos anos={proventosPorAno ?? []} />
        </>
      }
    />
  );
}

function formatarMes(mesIso: string): string {
  const [ano, mes] = mesIso.split('-');
  return `${mes}/${ano}`;
}

function CartaoMes({ item }: { item: ResumoMensalIR }) {
  const { ocultarValores } = useOcultarValores();
  const situacaoSwing = item.swingIsento ? '✅ Isento' : item.swingLucro < 0 ? '➖ Prejuízo' : '⚠️ Tributável';
  const corLucroSwing = item.swingLucro >= 0 ? cores.positivo : cores.negativo;

  return (
    <View style={estilos.cartaoMes}>
      <View style={estilos.linhaTopo}>
        <Text style={estilos.mes}>{formatarMes(item.mes)}</Text>
        {item.darfAPagar > 0 ? (
          <Text style={estilos.chipDarf}>DARF: {formatarMoeda(item.darfAPagar)}</Text>
        ) : item.abaixoDoMinimo ? (
          <Text style={estilos.chipMinimo}>Abaixo do mínimo (R$10)</Text>
        ) : null}
      </View>

      <View style={estilos.linhaDetalhe}>
        <Text style={estilos.rotuloDetalhe}>Swing Trade — {situacaoSwing}</Text>
        <Text style={[estilos.valorDetalhe, { color: corLucroSwing }]}>{formatarMoedaPriv(item.swingLucro, ocultarValores)}</Text>
      </View>

      {item.dayTradeLucro !== 0 && (
        <View style={estilos.linhaDetalhe}>
          <Text style={estilos.rotuloDetalhe}>Day Trade</Text>
          <Text style={[estilos.valorDetalhe, { color: item.dayTradeLucro >= 0 ? cores.positivo : cores.negativo }]}>
            {formatarMoedaPriv(item.dayTradeLucro, ocultarValores)}
          </Text>
        </View>
      )}

      <View style={estilos.linhaDetalhe}>
        <Text style={estilos.rotuloDetalheApagado}>IRRF estimado (crédito)</Text>
        <Text style={estilos.valorDetalheApagado}>{formatarMoeda(item.swingIrrf + item.dayTradeIrrf)}</Text>
      </View>
    </View>
  );
}

function SecaoBensEDireitos({ anos }: { anos: BensEDireitosAno[] }) {
  const { ocultarValores } = useOcultarValores();
  if (anos.length === 0) return null;
  return (
    <>
      <Text style={estilos.subtitulo}>Bens e Direitos (declaração anual)</Text>
      <Text style={estilos.legendaSecao}>Posição em 31/12 de cada ano fechado, pelo custo de aquisição.</Text>
      {anos.map((ano) => (
        <View key={ano.ano} style={estilos.cartaoAno}>
          <View style={estilos.linhaTopo}>
            <Text style={estilos.anoTitulo}>{ano.ano}</Text>
            <Text style={estilos.totalAno}>{formatarMoedaPriv(ano.totalInvestido, ocultarValores)}</Text>
          </View>
          {ano.posicoes.map((p) => (
            <View key={p.ticker} style={estilos.linhaDetalhe}>
              <Text style={estilos.rotuloDetalheApagado}>{p.ticker} · {formatarNumero(p.qtdTotal, 0)}x</Text>
              <Text style={estilos.valorDetalheApagado}>{formatarMoedaPriv(p.valorTotalInvestido, ocultarValores)}</Text>
            </View>
          ))}
        </View>
      ))}
    </>
  );
}

function SecaoProventos({ anos }: { anos: ProventosAno[] }) {
  const { ocultarValores } = useOcultarValores();
  if (anos.length === 0) return null;
  return (
    <>
      <Text style={estilos.subtitulo}>Proventos por Ano</Text>
      <Text style={estilos.legendaSecao}>Dividendos (isentos até R$50k/mês por empresa) e JCP (15% na fonte), para a declaração.</Text>
      {anos.map((ano) => (
        <View key={ano.ano} style={estilos.cartaoAno}>
          <Text style={estilos.anoTitulo}>{ano.ano}</Text>
          <View style={estilos.linhaDetalhe}>
            <Text style={estilos.rotuloDetalheApagado}>Dividendos</Text>
            <Text style={estilos.valorDetalheApagado}>{formatarMoedaPriv(ano.dividendos, ocultarValores)}</Text>
          </View>
          <View style={estilos.linhaDetalhe}>
            <Text style={estilos.rotuloDetalheApagado}>JCP</Text>
            <Text style={estilos.valorDetalheApagado}>{formatarMoedaPriv(ano.jcp, ocultarValores)}</Text>
          </View>
          {ano.rendimentosFii > 0 && (
            <View style={estilos.linhaDetalhe}>
              <Text style={estilos.rotuloDetalheApagado}>Rendimentos FII</Text>
              <Text style={estilos.valorDetalheApagado}>{formatarMoedaPriv(ano.rendimentosFii, ocultarValores)}</Text>
            </View>
          )}
        </View>
      ))}
    </>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14 },
  lista: { paddingHorizontal: espacamento.lg, paddingTop: espacamento.xl, paddingBottom: espacamento.xl * 2 },
  linhaTitulo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2, marginBottom: espacamento.md, lineHeight: 17 },
  cartaoAviso: {
    backgroundColor: '#3a2f0f',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.destaque,
    padding: espacamento.md,
    marginBottom: espacamento.sm,
  },
  textoAviso: { color: cores.destaque, fontSize: 12, lineHeight: 17 },
  subtitulo: { color: cores.destaque, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6, marginTop: espacamento.lg, marginBottom: espacamento.sm },
  legendaSecao: { color: cores.textoApagado, fontSize: 11, marginTop: -4, marginBottom: espacamento.sm, lineHeight: 15 },
  aviso: { color: cores.neutro, fontSize: 13, lineHeight: 19 },
  cartaoMes: {
    backgroundColor: cores.fundoCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    marginBottom: espacamento.sm,
  },
  cartaoAno: {
    backgroundColor: cores.fundoCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    marginBottom: espacamento.sm,
  },
  linhaTopo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  mes: { color: cores.texto, fontSize: 15, fontWeight: '700' },
  anoTitulo: { color: cores.texto, fontSize: 15, fontWeight: '700' },
  totalAno: { color: cores.texto, fontSize: 13, fontWeight: '700' },
  chipDarf: { color: cores.negativo, fontSize: 12, fontWeight: '700' },
  chipMinimo: { color: cores.neutro, fontSize: 11 },
  linhaDetalhe: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  rotuloDetalhe: { color: cores.textoSecundario, fontSize: 12 },
  valorDetalhe: { fontSize: 13, fontWeight: '700' },
  rotuloDetalheApagado: { color: cores.textoApagado, fontSize: 11 },
  valorDetalheApagado: { color: cores.textoSecundario, fontSize: 12 },
});
