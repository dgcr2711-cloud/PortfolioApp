import React, { useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { useEspacoTopo } from '../hooks/useEspacoTopo';
import { CardKpi } from '../components/CardKpi';
import { GraficoDonutAlocacao } from '../components/GraficoDonutAlocacao';
import { SegmentedControl } from '../components/SegmentedControl';
import { BotaoOcultarValores } from '../components/BotaoOcultarValores';
import { useOcultarValores } from '../contexts/OcultarValoresContext';
import { cores, espacamento } from '../theme';
import { formatarDataHora, formatarMoedaPriv, formatarNumero, formatarPct } from '../format';

/**
 * Tela inicial — espelha a aba "🏠 Visão Geral" do app do PC: os mesmos 5
 * KPIs e o mesmo Painel de Diagnóstico da Carteira (concentração/HHI,
 * setores, CAGR, drawdown, fundamentos ponderados).
 *
 * Somente leitura: quem registra compras, define preço teto etc. continua
 * sendo o app do PC — o celular é a "vitrine" pra consultar de qualquer
 * lugar, não um substituto da tela de gestão.
 */
export function VisaoGeralScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();
  const { ocultarValores } = useOcultarValores();
  const [agruparPor, setAgruparPor] = useState<'ativo' | 'setor'>('ativo');
  const espacoTopo = useEspacoTopo();

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

  const { totais, diagnostico } = snapshot;
  const corLucro = totais.lucro >= 0 ? cores.positivo : cores.negativo;
  const sinal = totais.lucro >= 0 ? '+' : '';
  const corCagr = (diagnostico.cagrAproximado ?? 0) >= 0 ? cores.positivo : cores.negativo;
  const corHhi = diagnostico.classificacaoHhi === 'baixa' ? cores.positivo : diagnostico.classificacaoHhi === 'moderada' ? cores.destaque : cores.negativo;

  // Mesmos dados do gráfico de "Alocação" da aba 📈 Carteira do PC: por
  // ativo (posições com valor atual > 0) ou por setor (já vem agregado no
  // snapshot, em diagnostico.setores).
  const alocacaoPorAtivo = snapshot.ativos
    .filter((a) => (a.atual ?? 0) > 0)
    .map((a) => ({ rotulo: a.ticker, valor: a.atual as number }));
  const alocacaoPorSetor = diagnostico.setores.map((s) => ({ rotulo: s.setor, valor: s.valor }));

  return (
    <ScrollView
      style={estilos.container}
      contentContainerStyle={[estilos.conteudo, { paddingTop: espacoTopo }]}
      refreshControl={<RefreshControl refreshing={false} onRefresh={() => {}} tintColor={cores.destaque} />}
    >
      <View style={estilos.linhaTitulo}>
        <View>
          <Text style={estilos.titulo}>Visão Geral</Text>
          <Text style={estilos.legenda}>Atualizado em {formatarDataHora(snapshot.atualizadoEm)}</Text>
        </View>
        <BotaoOcultarValores />
      </View>

      <View style={estilos.grade}>
        <CardKpi
          rotulo="Patrimônio Atual"
          valor={formatarMoedaPriv(totais.totalAtual, ocultarValores)}
          corValor={cores.destaque}
          destaque
        />
        <CardKpi
          rotulo="Resultado"
          valor={`${sinal}${formatarMoedaPriv(totais.lucro, ocultarValores)}`}
          corValor={corLucro}
          subvalor={`${sinal}${formatarPct(totais.rentabilidadePct)}`}
          corSub={corLucro}
        />
        <CardKpi rotulo="Proventos (12m)" valor={formatarMoedaPriv(totais.proventos12m, ocultarValores)} />
        <CardKpi
          rotulo="Variação do Dia"
          valor={`${totais.variacaoDiaReais >= 0 ? '+' : ''}${formatarMoedaPriv(totais.variacaoDiaReais, ocultarValores)}`}
          corValor={totais.variacaoDiaReais >= 0 ? cores.positivo : cores.negativo}
        />
      </View>

      <View style={estilos.painel}>
        <View style={estilos.cabecalhoAlocacao}>
          <Text style={estilos.tituloPainel}>📊 Alocação da Carteira</Text>
        </View>
        <SegmentedControl
          opcoes={[
            { valor: 'ativo', rotulo: 'Ativo' },
            { valor: 'setor', rotulo: 'Setor' },
          ]}
          selecionada={agruparPor}
          aoSelecionar={setAgruparPor}
        />
        <View style={estilos.espacoGrafico}>
          <GraficoDonutAlocacao
            dados={agruparPor === 'ativo' ? alocacaoPorAtivo : alocacaoPorSetor}
            rotuloCentral="Patrimônio"
            valorCentral={formatarMoedaPriv(totais.totalAtual, ocultarValores)}
          />
        </View>
      </View>

      <View style={estilos.painel}>
        <Text style={estilos.tituloPainel}>🏛️ Concentração &amp; Diversificação</Text>
        <LinhaDiagnostico
          rotulo="Maior posição"
          valor={diagnostico.maiorTicker ? `${diagnostico.maiorTicker} — ${formatarPct(diagnostico.maiorPesoPct)}` : '—'}
          cor={diagnostico.alertaConcentracao ? cores.negativo : cores.texto}
        />
        <LinhaDiagnostico
          rotulo="Índice de concentração (HHI)"
          valor={`${formatarNumero(diagnostico.indiceHhi, 3)} — ${diagnostico.classificacaoHhi}`}
          cor={corHhi}
        />
        {diagnostico.setores[0] && (
          <LinhaDiagnostico rotulo="Maior exposição setorial" valor={`${diagnostico.setores[0].setor} — ${formatarPct(diagnostico.setores[0].peso_pct)}`} />
        )}
        {diagnostico.alertaConcentracao && (
          <Text style={estilos.avisoConcentracao}>⚠️ Concentração acima do limite recomendado.</Text>
        )}
      </View>

      <View style={estilos.painel}>
        <Text style={estilos.tituloPainel}>📈 Desempenho &amp; Fundamentos</Text>
        <LinhaDiagnostico
          rotulo="CAGR aproximado"
          valor={diagnostico.cagrAproximado !== null ? formatarPct(diagnostico.cagrAproximado) : '— histórico insuficiente'}
          cor={diagnostico.cagrAproximado !== null ? corCagr : cores.neutro}
        />
        {diagnostico.maiorPerdaRegistrada !== null && (
          <LinhaDiagnostico rotulo="Maior perda registrada" valor={formatarPct(diagnostico.maiorPerdaRegistrada)} cor={cores.negativo} />
        )}
        {diagnostico.fundamentosPonderados.cobertura_pct > 0 ? (
          <>
            <LinhaDiagnostico rotulo="P/L médio ponderado" valor={formatarNumero(diagnostico.fundamentosPonderados.pl, 1)} />
            <LinhaDiagnostico
              rotulo="Dividend Yield médio"
              valor={diagnostico.fundamentosPonderados.dividend_yield !== null ? formatarPct(diagnostico.fundamentosPonderados.dividend_yield * 100) : '—'}
              cor={cores.destaque}
            />
          </>
        ) : (
          <Text style={estilos.textoApagado}>Busque fundamentos na aba Fundamentos do app do PC.</Text>
        )}
      </View>
    </ScrollView>
  );
}

function LinhaDiagnostico({ rotulo, valor, cor = cores.texto }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <View style={estilos.linha}>
      <Text style={estilos.rotuloLinha}>{rotulo}</Text>
      <Text style={[estilos.valorLinha, { color: cor }]}>{valor}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  conteudo: { padding: espacamento.lg },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14, lineHeight: 20 },
  linhaTitulo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: espacamento.lg },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2 },
  grade: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamento.md },
  painel: {
    backgroundColor: '#161d2b',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(212,175,55,0.25)',
    padding: espacamento.lg,
    marginTop: espacamento.md,
  },
  tituloPainel: { color: cores.destaque, fontSize: 12, fontWeight: '700', letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: espacamento.sm },
  cabecalhoAlocacao: { marginBottom: espacamento.xs },
  espacoGrafico: { marginTop: espacamento.md },
  linha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 7,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255,255,255,0.08)',
  },
  rotuloLinha: { color: '#c3cad6', fontSize: 13, flexShrink: 1, paddingRight: espacamento.sm },
  valorLinha: { fontWeight: '700', fontSize: 13 },
  avisoConcentracao: { color: cores.negativo, fontSize: 12, marginTop: espacamento.sm },
  textoApagado: { color: cores.textoApagado, fontSize: 12, marginTop: espacamento.xs },
});
