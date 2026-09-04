import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { cores, espacamento } from '../theme';
import type { ItemMapaDividendos, ItemMapaSomenteAnunciado, MapaDividendos as MapaDividendosTipo } from '../types';

const MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const LARGURA_CELULA = 26;
const LARGURA_TICKER = 62;

/** Mesma escala de opacidade do verde usada no mapa do site (ui/proventos.py::_opacidade_mes_pago). */
function corVerde(contagem: number): string {
  const opacidade = Math.min(0.16 + 0.14 * (contagem - 1), 0.6);
  return `rgba(52,211,153,${opacidade})`;
}

type LinhaMapa = {
  ticker: string;
  setor: string;
  contagemPorMes: Record<string, number>;
  mesesAnunciados: number[];
};

/**
 * Espelha o "🗓️ Mapa de Dividendos — histórico mês a mês" da aba
 * Proventos do PC (2026-09-04, Diego pediu pra ter no fim da aba Preço
 * Teto do celular): grade Ticker x Mês, agrupada por setor. 🟢 verde
 * sólido = mês em que já foi registrado um provento (quanto mais vezes,
 * mais forte); 🔵 borda tracejada azul = mês anunciado pela B3 mas ainda
 * não registrado. A grade rola na horizontal — 12 meses + coluna de
 * ticker não cabem numa tela de celular de uma vez só.
 */
export function MapaDividendos({ mapa }: { mapa: MapaDividendosTipo | undefined }) {
  if (!mapa || (mapa.porTicker.length === 0 && mapa.somenteAnunciados.length === 0)) {
    return null; // snapshot antigo (sem esse campo) ou nenhum provento/anúncio ainda
  }

  const linhas: LinhaMapa[] = [
    ...mapa.porTicker.map((item: ItemMapaDividendos) => ({
      ticker: item.ticker,
      setor: item.setor,
      contagemPorMes: item.contagemPorMes,
      mesesAnunciados: item.mesesAnunciados,
    })),
    ...mapa.somenteAnunciados.map((item: ItemMapaSomenteAnunciado) => ({
      ticker: item.ticker,
      setor: item.setor,
      contagemPorMes: {},
      mesesAnunciados: item.mesesAnunciados,
    })),
  ];

  const porSetor = new Map<string, LinhaMapa[]>();
  for (const linha of linhas) {
    const lista = porSetor.get(linha.setor) ?? [];
    lista.push(linha);
    porSetor.set(linha.setor, lista);
  }
  const setoresOrdenados = [...porSetor.keys()].sort();

  return (
    <View style={estilos.container}>
      <Text style={estilos.subtitulo}>🗓️ Mapa de Dividendos</Text>
      <Text style={estilos.legenda}>🟢 já registrado · 🔵 anunciado pela B3 (ainda não registrado)</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator style={estilos.rolagem}>
        <View>
          <View style={estilos.linha}>
            <View style={estilos.celulaTicker} />
            {MESES_ABREV.map((mes) => (
              <View key={mes} style={estilos.celulaCabecalho}>
                <Text style={estilos.textoCabecalho}>{mes}</Text>
              </View>
            ))}
          </View>

          {setoresOrdenados.map((setor) => (
            <View key={setor}>
              <Text style={estilos.rotuloSetor}>{setor}</Text>
              {[...(porSetor.get(setor) ?? [])]
                .sort((a, b) => a.ticker.localeCompare(b.ticker))
                .map((linha) => (
                  <View key={linha.ticker} style={estilos.linha}>
                    <View style={estilos.celulaTicker}>
                      <Text style={estilos.textoTicker} numberOfLines={1}>
                        {linha.ticker}
                      </Text>
                    </View>
                    {MESES_ABREV.map((_, indice) => {
                      const mes = indice + 1;
                      const contagem = linha.contagemPorMes[String(mes)] ?? 0;
                      const anunciado = linha.mesesAnunciados.includes(mes);
                      if (contagem > 0) {
                        return <View key={mes} style={[estilos.celula, { backgroundColor: corVerde(contagem) }]} />;
                      }
                      if (anunciado) {
                        return <View key={mes} style={[estilos.celula, estilos.celulaAnunciada]} />;
                      }
                      return <View key={mes} style={estilos.celula} />;
                    })}
                  </View>
                ))}
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { marginTop: espacamento.xl },
  subtitulo: {
    color: cores.destaque,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 4,
  },
  legenda: { color: cores.textoApagado, fontSize: 11, marginBottom: espacamento.sm },
  rolagem: { borderRadius: 12, borderWidth: 1, borderColor: cores.borda, backgroundColor: cores.fundoCard },
  linha: { flexDirection: 'row', alignItems: 'center' },
  celulaTicker: {
    width: LARGURA_TICKER,
    paddingHorizontal: 6,
    paddingVertical: 4,
    justifyContent: 'center',
  },
  textoTicker: { color: cores.texto, fontSize: 11, fontWeight: '700' },
  celulaCabecalho: { width: LARGURA_CELULA, alignItems: 'center', paddingVertical: 6 },
  textoCabecalho: { color: cores.textoApagado, fontSize: 9 },
  celula: {
    width: LARGURA_CELULA,
    height: LARGURA_CELULA,
    margin: 2,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  celulaAnunciada: {
    backgroundColor: 'rgba(56,189,248,0.14)',
    borderWidth: 1,
    borderColor: cores.info,
    borderStyle: 'dashed',
  },
  rotuloSetor: {
    color: cores.textoSecundario,
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.3,
    marginTop: espacamento.sm,
    marginBottom: 2,
    paddingLeft: 2,
  },
});
