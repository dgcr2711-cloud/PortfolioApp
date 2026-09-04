// Stub mínimo de firebase/app para o harness de verificação (2026-09-04) —
// ver nota em ../react/index.d.ts.
declare module 'firebase/app' {
  export interface FirebaseApp {
    name: string;
  }
  export function initializeApp(config: any): FirebaseApp;
}
