import React, { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { cores, espacamento } from '../theme';

/**
 * Seção recolhível simples — cabeçalho tocável (título + seta ▸/▾) que
 * mostra/esconde o conteúdo abaixo. Usado em mais de uma tela (Carteira,
 * Evolução) então virou um componente próprio em vez de duplicar o mesmo
 * `useState` + `TouchableOpacity` em cada uma.
 *
 * 2026-09-04: criado a pedido do Diego — "Metas de Alocação" (Carteira)
 * ganhou um filtro pra abrir só quando quiser, e "O que isso significa?"
 * (Evolução, explicação de Beta/Sharpe) precisava do mesmo padrão já
 * usado no site (`st.expander`).
 */
export function Expansor({
  titulo,
  abertoPorPadrao = false,
  children,
}: {
  titulo: string;
  abertoPorPadrao?: boolean;
  children: React.ReactNode;
}) {
  const [aberto, setAberto] = useState(abertoPorPadrao);

  return (
    <View style={estilos.container}>
      <TouchableOpacity style={estilos.cabecalho} onPress={() => setAberto((a) => !a)} activeOpacity={0.7}>
        <Text style={estilos.titulo}>{titulo}</Text>
        <Text style={estilos.seta}>{aberto ? '▾' : '▸'}</Text>
      </TouchableOpacity>
      {aberto && <View style={estilos.conteudo}>{children}</View>}
    </View>
  );
}

const estilos = StyleSheet.create({
  container: {
    backgroundColor: cores.fundoCard,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: cores.borda,
    marginBottom: espacamento.md,
    overflow: 'hidden',
  },
  cabecalho: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: espacamento.lg,
  },
  titulo: { color: cores.destaque, fontSize: 13, fontWeight: '700' },
  seta: { color: cores.textoApagado, fontSize: 14 },
  conteudo: { paddingHorizontal: espacamento.lg, paddingBottom: espacamento.lg },
});
