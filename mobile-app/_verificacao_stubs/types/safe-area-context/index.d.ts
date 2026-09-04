// Stub mínimo de react-native-safe-area-context para o harness de
// verificação (2026-09-04, adicionado pra checar useEspacoTopo.ts/
// MaisScreen.tsx) — ver nota em ../react/index.d.ts.
declare module 'react-native-safe-area-context' {
  export interface EdgeInsets {
    top: number;
    bottom: number;
    left: number;
    right: number;
  }
  export function useSafeAreaInsets(): EdgeInsets;
  export const SafeAreaProvider: any;
  export const SafeAreaView: any;
}
