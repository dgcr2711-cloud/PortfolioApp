// Stub mínimo de react-native para o harness de verificação — ver nota em
// ../react/index.d.ts. Componentes tipados frouxamente de propósito (props:
// any) porque o objetivo aqui é pegar erro de LÓGICA no nosso código
// (campo inexistente, variável não definida, tipo trocado), não replicar a
// tipagem inteira do react-native.
declare module 'react-native' {
  export const View: any;
  export const Text: any;
  export const TextInput: any;
  export const TouchableOpacity: any;
  export const ScrollView: any;
  export const ActivityIndicator: any;
  export const KeyboardAvoidingView: any;
  export const FlatList: any;
  export const RefreshControl: any;
  export const Alert: { alert: (...args: any[]) => void };
  export const Platform: { OS: 'ios' | 'android' | 'web'; select: (obj: any) => any };
  export const StyleSheet: { create: <T extends Record<string, any>>(styles: T) => T; hairlineWidth: number };
  export type AppStateStatus = 'active' | 'background' | 'inactive' | 'extension' | 'unknown';
  export const AppState: {
    currentState: AppStateStatus;
    addEventListener: (tipo: 'change', callback: (estado: AppStateStatus) => void) => { remove: () => void };
  };
}
