declare module 'react-native-svg' {
  import { Component } from 'react';
  import { ViewStyle } from 'react-native';

  export interface SvgProps {
    width?: number | string;
    height?: number | string;
    viewBox?: string;
    style?: ViewStyle | ViewStyle[];
    children?: any;
  }

  export default class Svg extends Component<SvgProps> {}

  export interface CircleProps {
    cx?: number | string;
    cy?: number | string;
    r?: number | string;
    stroke?: string;
    strokeWidth?: number | string;
    strokeDasharray?: string | number[];
    strokeDashoffset?: number | string;
    strokeLinecap?: 'butt' | 'round' | 'square';
    fill?: string;
  }

  export class Circle extends Component<CircleProps> {}
  export class G extends Component<any> {}
  export class Path extends Component<any> {}
  export class Rect extends Component<any> {}
  export class Text extends Component<any> {}
  // 2026-09-04 (GraficoLinhaSvg.tsx — gráfico de linha da Evolução e do
  // Preço Teto): componentes extras da lib de verdade que este stub ainda
  // não tinha, porque nenhum componente daqui os usava até agora.
  export class Line extends Component<any> {}
  export class Defs extends Component<any> {}
  export class LinearGradient extends Component<any> {}
  export class Stop extends Component<any> {}
}
