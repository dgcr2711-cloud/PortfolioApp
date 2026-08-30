import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { cores, espacamento } from '../theme';

/**
 * Alternador simples entre 2-3 sub-telas dentro de UMA aba da barra inferior
 * — usado pra caber mais funcionalidades sem estourar o número de ícones lá
 * embaixo (ex: aba "Compras" alterna entre "Nova" e "Histórico"). Guarda o
 * estado (qual opção está selecionada) no componente pai, via `useState`.
 */
export function SegmentedControl<T extends string>({
  opcoes,
  selecionada,
  aoSelecionar,
}: {
  opcoes: { valor: T; rotulo: string }[];
  selecionada: T;
  aoSelecionar: (valor: T) => void;
}) {
  return (
    <View style={estilos.container}>
      {opcoes.map((opcao) => {
        const ativa = opcao.valor === selecionada;
        return (
          <TouchableOpacity
            key={opcao.valor}
            style={[estilos.opcao, ativa && estilos.opcaoAtiva]}
            onPress={() => aoSelecionar(opcao.valor)}
          >
            <Text style={[estilos.texto, ativa && estilos.textoAtivo]}>{opcao.rotulo}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const estilos = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: 3,
    gap: 3,
  },
  opcao: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  opcaoAtiva: { backgroundColor: 'rgba(212,175,55,0.16)' },
  texto: { color: cores.textoSecundario, fontWeight: '600', fontSize: 13 },
  textoAtivo: { color: cores.destaque },
  espacador: { height: espacamento.md },
});
