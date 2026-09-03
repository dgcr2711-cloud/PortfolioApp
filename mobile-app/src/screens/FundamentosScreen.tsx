import React, { useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { useEspacoTopo } from '../hooks/useEspacoTopo';
import { cores, espacamento } from '../theme';
import { formatarMoeda, formatarNumero, formatarPct } from '../format';
import type { Ativo, FundamentosAtivo } from '../types';

/**
 * Espelha a aba 🔎 Fundamentos do PC por inteiro: o resumo ponderado da
 * carteira E a tabela "Indicadores por Ativo" (aqui em formato de cartão,
 * mais fácil de ler numa tela pequena que uma tabela de 10 colunas).
 *
 * Os números vêm prontos no snapshot (core/mobile_snapshot.py) — o celular
 * só formata e exibe, nunca recalcula nada. Quem busca os fundamentos
 * continua sendo o botão "🔄 Atualizar Fundamentos" do app do PC.
 */
export function FundamentosScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();
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

  const fp = snapshot.diagnostico.fundamentosPonderados;
  const resumo = [
    { rotulo: 'P/L médio ponderado', valor: fp.pl !== null ? fp.pl.toFixed(1) : '—' },
    { rotulo: 'P/VP médio ponderado', valor: fp.pvp !== null ? fp.pvp.toFixed(2) : '—' },
    { rotulo: 'Dividend Yield médio', valor: fp.dividend_yield !== null ? formatarPct(fp.dividend_yield * 100) : '—' },
    { rotulo: 'ROE médio ponderado', valor: fp.roe !== null ? formatarPct(fp.roe * 100) : '—' },
    { rotulo: 'Cobertura da carteira', valor: formatarPct(fp.cobertura_pct) },
  ];

  return (
    <FlatList
      style={estilos.container}
      contentContainerStyle={[estilos.lista, { paddingTop: espacoTopo }]}
      data={snapshot.ativos}
      keyExtractor={(item: Ativo) => item.ticker}
      ListHeaderComponent={
        <>
          <Text style={estilos.titulo}>Fundamentos</Text>
          <Text style={estilos.legenda}>A empresa por trás do preço é um bom negócio? Resumo da carteira e indicadores por ativo.</Text>

          {fp.cobertura_pct === 0 ? (
            <Text style={estilos.aviso}>Ainda não há fundamentos buscados. Clique em "🔄 Atualizar Fundamentos" no app do PC.</Text>
          ) : (
            <View style={estilos.blocoResumo}>
              {resumo.map((item) => (
                <View key={item.rotulo} style={estilos.linhaResumo}>
                  <Text style={estilos.rotuloLinha}>{item.rotulo}</Text>
                  <Text style={estilos.valorLinha}>{item.valor}</Text>
                </View>
              ))}
            </View>
          )}

          {snapshot.diagnostico.setores.length > 0 && (
            <>
              <Text style={estilos.subtitulo}>Diversificação Setorial</Text>
              <View style={estilos.blocoResumo}>
                {snapshot.diagnostico.setores.map((item) => (
                  <View key={item.setor} style={estilos.linhaResumo}>
                    <Text style={estilos.rotuloLinha}>{item.setor}</Text>
                    <Text style={estilos.valorLinha}>{formatarPct(item.peso_pct)}</Text>
                  </View>
                ))}
              </View>
            </>
          )}

          {snapshot.ativos.length > 0 && <Text style={estilos.subtitulo}>Indicadores por Ativo</Text>}
        </>
      }
      renderItem={({ item }: { item: Ativo }) => <CartaoFundamentos ativo={item} />}
    />
  );
}

function CartaoFundamentos({ ativo }: { ativo: Ativo }) {
  const f = ativo.fundamentos;
  const [mostrarAvancada, setMostrarAvancada] = useState(false);
  const temAnaliseAvancada = Boolean(ativo.piotroski || ativo.altman || ativo.footballField);

  return (
    <View style={estilos.cartao}>
      <View style={estilos.linhaTopo}>
        <Text style={estilos.ticker}>
          {ativo.ticker} {ativo.ehAlvo ? '🎯' : ''}
        </Text>
        {f?.setorYahoo && <Text style={estilos.setor}>{f.setorYahoo}</Text>}
      </View>

      {!f ? (
        <Text style={estilos.textoApagado}>— sem fundamentos buscados ainda</Text>
      ) : (
        <>
          <View style={estilos.grade}>
            <Campo rotulo="P/L" valor={formatarNumero(f.pl, 1)} />
            <Campo rotulo="P/L proj." valor={formatarNumero(f.plProjetado, 1)} />
            <Campo rotulo="P/VP" valor={formatarNumero(f.pvp, 2)} />
            <Campo rotulo="Div. Yield" valor={f.dividendYield !== null ? formatarPct(f.dividendYield * 100) : '—'} cor={cores.destaque} />
            <Campo rotulo="Payout" valor={f.payoutRatio !== null ? formatarPct(f.payoutRatio * 100) : '—'} />
            <Campo rotulo="Payout (12m calc.)" valor={f.payoutTtmCalculado !== null ? formatarPct(f.payoutTtmCalculado * 100) : '—'} />
            <Campo rotulo="ROE" valor={f.roe !== null ? formatarPct(f.roe * 100) : '—'} />
            <Campo
              rotulo="Margem Líq."
              valor={f.margemLiquida !== null ? formatarPct(f.margemLiquida * 100) : '—'}
              cor={(f.margemLiquida ?? 0) > 0 ? cores.positivo : cores.negativo}
            />
            <Campo
              rotulo="Dívida/PL"
              valor={f.dividaPatrimonio !== null ? `${formatarNumero(f.dividaPatrimonio, 0)}%` : '—'}
              cor={f.dividaPatrimonio === null ? cores.texto : f.dividaPatrimonio < 100 ? cores.positivo : cores.negativo}
            />
            <Campo rotulo="Valor de Mercado" valor={formatarValorMercado(f.valorMercado)} />
            <Campo rotulo="Beta" valor={formatarNumero(f.beta, 2)} />
            <Campo rotulo="Faixa 52 sem." valor={formatarFaixa52s(f)} />
          </View>

          <Text style={estilos.subtituloCartao}>🎯 Indicadores para o Preço Teto</Text>
          <View style={estilos.grade}>
            <Campo rotulo="FCF Livre (12m)" valor={formatarValorGrande(f.freeCashflow)} />
            <Campo
              rotulo="Dívida Líquida"
              valor={formatarValorGrande(f.dividaLiquida)}
              cor={f.dividaLiquida === null ? cores.texto : f.dividaLiquida <= 0 ? cores.positivo : cores.negativo}
            />
            <Campo rotulo="Nº de Ações" valor={f.numAcoes ? `${formatarNumero(f.numAcoes / 1e6, 1)} mi` : '—'} />
            <Campo rotulo="Cresc. Receita" valor={f.crescimentoReceita !== null ? formatarPct(f.crescimentoReceita * 100) : '—'} />
          </View>

          {temAnaliseAvancada && (
            <>
              <TouchableOpacity onPress={() => setMostrarAvancada((v) => !v)} style={estilos.linhaToggleAvancada}>
                <Text style={estilos.linkAnaliseAvancada}>
                  {mostrarAvancada ? '▾' : '▸'} Análise Avançada (Piotroski / Altman / Football Field)
                </Text>
              </TouchableOpacity>
              {mostrarAvancada && <AnaliseAvancada ativo={ativo} />}
            </>
          )}
        </>
      )}
    </View>
  );
}

function AnaliseAvancada({ ativo }: { ativo: Ativo }) {
  return (
    <View style={estilos.blocoAvancado}>
      {ativo.piotroski && (
        <View style={estilos.subBlocoAvancado}>
          <Text style={estilos.subtituloCartao}>🧾 Piotroski F-Score</Text>
          <Text style={[estilos.valorDestaqueAvancado, { color: corClassificacaoPiotroski(ativo.piotroski.classificacao) }]}>
            {ativo.piotroski.pontos}/{ativo.piotroski.totalAvaliado} — {ativo.piotroski.classificacao}
          </Text>
          {ativo.piotroski.criterios.map((c) => (
            <Text key={c.chave} style={estilos.linhaCriterio}>
              {c.passou === true ? '✅' : c.passou === false ? '❌' : '➖'} {c.rotulo}
            </Text>
          ))}
        </View>
      )}

      {ativo.altman && (
        <View style={estilos.subBlocoAvancado}>
          <Text style={estilos.subtituloCartao}>⚠️ Altman Z-Score</Text>
          <Text style={[estilos.valorDestaqueAvancado, { color: corClassificacaoAltman(ativo.altman.classificacao) }]}>
            {ativo.altman.zScore !== null ? ativo.altman.zScore.toFixed(2) : '—'} — {ativo.altman.classificacao}
          </Text>
          {ativo.setor === 'Bancos' && (
            <Text style={estilos.avisoBanco}>
              ⚠️ Modelo calibrado para indústria — leitura para bancos costuma não fazer sentido.
            </Text>
          )}
        </View>
      )}

      {ativo.footballField && (
        <View style={estilos.subBlocoAvancado}>
          <Text style={estilos.subtituloCartao}>🏈 Football Field de Valuation</Text>
          {ativo.footballField.metodos.map((m) => (
            <View key={m.nome} style={estilos.linhaMetodo}>
              <Text style={estilos.rotuloMetodo}>{m.nome}</Text>
              <Text style={estilos.valorMetodo}>{formatarMoeda(m.precoJusto)}</Text>
            </View>
          ))}
          <Text style={estilos.faixaFootballField}>
            Faixa: {formatarMoeda(ativo.footballField.minimo)} – {formatarMoeda(ativo.footballField.maximo)}{' '}
            (média: {formatarMoeda(ativo.footballField.media)})
          </Text>
        </View>
      )}
    </View>
  );
}

// Mesmo mapeamento classificação → cor do app do PC (ui/fundamentos.py) —
// antes disto, os dois mostravam a classificação em branco/neutro, sem
// nenhuma pista visual rápida de "isso é bom ou ruim".
function corClassificacaoPiotroski(classificacao: string): string {
  if (classificacao === 'Forte') return cores.positivo;
  if (classificacao === 'Fraca') return cores.negativo;
  if (classificacao === 'Neutra') return cores.neutro;
  return cores.neutro;
}

function corClassificacaoAltman(classificacao: string): string {
  if (classificacao === 'Zona Segura') return cores.positivo;
  if (classificacao === 'Zona de Alerta') return cores.destaque;
  if (classificacao === 'Zona de Risco') return cores.negativo;
  return cores.neutro;
}

function formatarValorGrande(valor: number | null): string {
  if (valor === null || !Number.isFinite(valor)) return '—';
  const sinal = valor < 0 ? '-' : '';
  const absoluto = Math.abs(valor);
  if (absoluto >= 1e9) return `${sinal}R$ ${(absoluto / 1e9).toFixed(1)} bi`;
  if (absoluto >= 1e6) return `${sinal}R$ ${(absoluto / 1e6).toFixed(0)} mi`;
  if (absoluto >= 1e3) return `${sinal}R$ ${(absoluto / 1e3).toFixed(0)} mil`;
  return `${sinal}R$ ${absoluto.toFixed(0)}`;
}

function formatarValorMercado(valor: number | null): string {
  if (valor === null || !Number.isFinite(valor)) return '—';
  if (valor >= 1e9) return `R$ ${(valor / 1e9).toFixed(1)} bi`;
  if (valor > 0) return `R$ ${(valor / 1e6).toFixed(0)} mi`;
  return '—';
}

function formatarFaixa52s(f: FundamentosAtivo): string {
  if (f.minima52s === null || f.maxima52s === null) return '—';
  return `${formatarNumero(f.minima52s, 2)} – ${formatarNumero(f.maxima52s, 2)}`;
}

function Campo({ rotulo, valor, cor = cores.texto }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <View style={estilos.campo}>
      <Text style={estilos.rotuloCampo}>{rotulo}</Text>
      <Text style={[estilos.valorCampo, { color: cor }]}>{valor}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14 },
  lista: { paddingHorizontal: espacamento.lg, paddingBottom: espacamento.xl },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2, marginBottom: espacamento.lg, lineHeight: 17 },
  subtitulo: { color: cores.destaque, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6, marginTop: espacamento.lg, marginBottom: espacamento.sm },
  aviso: { color: cores.neutro, fontSize: 13, lineHeight: 19 },
  blocoResumo: { gap: espacamento.sm },
  linhaResumo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
  },
  rotuloLinha: { color: '#c3cad6', fontSize: 13 },
  valorLinha: { color: cores.texto, fontWeight: '700', fontSize: 13 },
  cartao: {
    backgroundColor: cores.fundoCard,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.lg,
    marginBottom: espacamento.md,
  },
  linhaTopo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  ticker: { color: cores.texto, fontSize: 16, fontWeight: '700' },
  setor: { color: cores.textoSecundario, fontSize: 11 },
  textoApagado: { color: cores.textoApagado, fontSize: 12, marginTop: espacamento.sm },
  subtituloCartao: {
    color: cores.textoApagado, fontSize: 10, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.3,
    marginTop: espacamento.md, borderTopWidth: 1, borderTopColor: cores.borda, paddingTop: espacamento.sm,
  },
  grade: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamento.md, marginTop: espacamento.md },
  campo: { minWidth: '40%' },
  rotuloCampo: { color: cores.textoApagado, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.3 },
  valorCampo: { fontSize: 14, fontWeight: '600', marginTop: 2 },
  linhaToggleAvancada: {
    marginTop: espacamento.md, borderTopWidth: 1, borderTopColor: cores.borda, paddingTop: espacamento.sm,
  },
  linkAnaliseAvancada: { color: cores.destaque, fontSize: 12, fontWeight: '600' },
  blocoAvancado: { marginTop: espacamento.sm, gap: espacamento.md },
  subBlocoAvancado: { gap: 4 },
  valorDestaqueAvancado: { color: cores.texto, fontSize: 14, fontWeight: '700', marginTop: 2 },
  linhaCriterio: { color: cores.textoSecundario, fontSize: 12, marginTop: 2 },
  avisoBanco: { color: cores.neutro, fontSize: 11, lineHeight: 15, marginTop: 2 },
  linhaMetodo: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 2 },
  rotuloMetodo: { color: cores.textoSecundario, fontSize: 12 },
  valorMetodo: { color: cores.texto, fontSize: 12, fontWeight: '600' },
  faixaFootballField: { color: cores.destaque, fontSize: 12, fontWeight: '700', marginTop: espacamento.xs },
});
