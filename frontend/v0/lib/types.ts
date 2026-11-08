export type RiskLevel = 'alto' | 'medio' | 'baixo';

export type SignalStatus = 
  | 'informado' 
  | 'em_analise' 
  | 'em_monitoramento' 
  | 'evento_confirmado' 
  | 'descartado';

export type SignalSource = 
  | 'EIOS' 
  | 'Guardiões da Saúde' 
  | 'Twitter/X' 
  | 'Facebook' 
  | 'WhatsApp' 
  | 'Jornal' 
  | 'Portal de Notícias'
  | 'Unidade de Saúde'
  | 'Outro';

export type SignalType = 
  | 'Abertura' 
  | 'Atualização' 
  | 'Encerramento';

export type Confidentiality = 
  | 'Nível 1' 
  | 'Nível 2' 
  | 'Nível 3';

export interface Signal {
  id: string;
  title: string;
  description: string;
  status: SignalStatus;
  riskLevel: RiskLevel;
  source: SignalSource;
  signalType: SignalType;
  confidentiality: Confidentiality;
  etiology?: string;
  generalDanger?: string;
  specificDanger?: string;
  tags: string[];
  
  // Location
  countries: string[];
  states: string[];
  municipalities: string[];
  originCountry?: string;
  address?: string;
  
  // Dates
  signalDate: string;
  detectionDate: string;
  notificationDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface KanbanColumn {
  id: SignalStatus;
  title: string;
  color: string;
  signals: Signal[];
}

export const STATUS_CONFIG: Record<SignalStatus, { title: string; color: string; bgColor: string }> = {
  informado: {
    title: 'Informados (Entrada)',
    color: 'bg-status-informed',
    bgColor: 'bg-blue-50',
  },
  em_analise: {
    title: 'Em Análise',
    color: 'bg-status-analysis',
    bgColor: 'bg-amber-50',
  },
  em_monitoramento: {
    title: 'Em Monitoramento',
    color: 'bg-status-monitoring',
    bgColor: 'bg-cyan-50',
  },
  evento_confirmado: {
    title: 'Eventos Confirmados',
    color: 'bg-status-confirmed',
    bgColor: 'bg-red-50',
  },
  descartado: {
    title: 'Descartados',
    color: 'bg-status-discarded',
    bgColor: 'bg-gray-50',
  },
};

export const RISK_CONFIG: Record<RiskLevel, { label: string; color: string; bgColor: string }> = {
  alto: {
    label: 'Alto',
    color: 'text-white',
    bgColor: 'bg-risk-high',
  },
  medio: {
    label: 'Médio',
    color: 'text-white',
    bgColor: 'bg-risk-medium',
  },
  baixo: {
    label: 'Baixo',
    color: 'text-white',
    bgColor: 'bg-risk-low',
  },
};

