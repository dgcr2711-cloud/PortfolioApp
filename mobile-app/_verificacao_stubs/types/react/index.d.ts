// Stub mínimo de React só para o harness de verificação (tsc --strict) rodar
// neste sandbox, onde `npm install` não funciona (registry bloqueado). NÃO é
// shipado com o app — o app real usa os @types/react de verdade via npm.
//
// Limitação conhecida: como este stub não replica o mecanismo real de
// "LibraryManagedAttributes" do React para JSX, o tsc acusa falsamente
// "Property 'children' is missing" em componentes que recebem children via
// JSX aninhado (em vez de via prop explícita). Isso é um falso-positivo do
// harness — não do código — reconhecível porque aparece igual em arquivos
// já revisados e inalterados (ex: NovaCompraScreen.tsx).
//
// 2026-09-04: segunda classe do MESMO problema, agora com "key" — "Property
// 'key' does not exist" em componentes próprios usados dentro de `.map()`
// com `key={...}` (React sempre aceita `key` em qualquer componente, sem
// precisar declarar no tipo de props — via `React.Attributes`/
// `JSX.IntrinsicAttributes` na tipagem real). Tentei corrigir via
// `declare global { namespace JSX { interface IntrinsicAttributes {
// key?: ... } } }` (abaixo) — funciona num arquivo isolado, mas não some
// aqui porque o `React` usado como fábrica do JSX vem de um `import ...
// from 'react'` apontando pra este stub (não pro pacote @types/react de
// verdade), e o tsc resolve o namespace `JSX` a partir do módulo da
// fábrica antes de cair pro global nesse cenário. Resultado: "key" segue
// como falso-positivo conhecido do harness, IGUAL ao de "children" acima
// — confirmado seguro por revisão manual (é o padrão padrão do React,
// funciona normal com @types/react de verdade, que é o que o app real
// usa via npm).
declare namespace React {
  type ReactNode = any;
  type FC<P = any> = (props: P) => any;
  // 2026-09-04 (GraficoLinhaSvg.tsx — mesmo cast usado em
  // GraficoDonutAlocacao.tsx pros componentes de react-native-svg):
  // faltava no stub, só usado como tipo do cast `as unknown as
  // React.ComponentType<any>`, nunca instanciado de verdade aqui.
  type ComponentType<P = any> = (props: P) => any;
  type Dispatch<A> = (value: A) => void;
  type SetStateAction<S> = S | ((prevState: S) => S);
}

declare module 'react' {
  export type ReactNode = React.ReactNode;
  export type FC<P = any> = React.FC<P>;
  export type ComponentType<P = any> = React.ComponentType<P>;
  export type Dispatch<A> = React.Dispatch<A>;
  export type SetStateAction<S> = React.SetStateAction<S>;

  export function useState<S>(initial: S | (() => S)): [S, Dispatch<SetStateAction<S>>];
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useRef<T>(initial: T): { current: T };
  export function useMemo<T>(factory: () => T, deps: any[]): T;
  export interface Context<T> {
    Provider: FC<{ value: T; children?: ReactNode }>;
    Consumer: FC<{ children: (value: T) => ReactNode }>;
  }
  export function createContext<T>(defaultValue: T): Context<T>;
  export function useContext<T>(context: Context<T>): T;

  const ReactDefault: {
    createElement: (...args: any[]) => any;
  };
  export default ReactDefault;
}

// Faz o `key={...}` ser aceito em qualquer elemento JSX (componente próprio
// incluso), igual ao comportamento real do React/@types/react — sem isso,
// o tsc acusa falsamente "Property 'key' does not exist" em componentes
// próprios usados dentro de `.map()`.
declare global {
  namespace JSX {
    interface IntrinsicAttributes {
      key?: string | number | null;
    }
  }
}
