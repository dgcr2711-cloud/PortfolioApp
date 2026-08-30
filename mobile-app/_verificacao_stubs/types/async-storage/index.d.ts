// Stub mínimo de @react-native-async-storage/async-storage para o harness
// de verificação — ver nota em ../react/index.d.ts. Só a API realmente
// usada no projeto (getItem/setItem/removeItem), com o mesmo formato
// baseado em Promises da biblioteca real.
declare module '@react-native-async-storage/async-storage' {
  const AsyncStorage: {
    getItem: (chave: string) => Promise<string | null>;
    setItem: (chave: string, valor: string) => Promise<void>;
    removeItem: (chave: string) => Promise<void>;
  };
  export default AsyncStorage;
}
