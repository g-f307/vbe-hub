import type {
  AuditEvent,
  GroupingCriterion,
  NeighborhoodSummary,
  PipelineMetric,
  QueueIndicator,
  RelationSuggestion,
  Signal,
  SourceRecord,
  SourceType,
  TechnicalSheet,
} from './types'

export const MUNICIPALITY = 'Manaus'
export const LAST_UPDATED_ISO = '2026-10-07T14:32:00-04:00'
export const EXTRACTION_VERSION = 'extrator-vbe 0.9.3'

type SourceSeed = {
  id: string
  code: string
  type: SourceType
  subtype: string
  title: string
  excerpt: string
  origin: string
  publishedAt: string
  neighborhood: string
  isContext?: boolean
  relation: RelationSuggestion
  sheet: Omit<TechnicalSheet, 'extractionVersion' | 'extractedAt'>
}

type SignalSeed = Omit<Signal, 'sourceIds' | 'municipality' | 'slug'> & {
  sources: SourceSeed[]
}

function sheetFrom(seed: SourceSeed): TechnicalSheet {
  return {
    ...seed.sheet,
    extractionVersion: EXTRACTION_VERSION,
    extractedAt: seed.publishedAt,
  }
}

const criteria = (
  sintomas: [boolean, string],
  area: [boolean, string],
  periodo: [boolean, string],
  fontes: [boolean, string],
): GroupingCriterion[] => [
  { label: 'Sintomas compatíveis', met: sintomas[0], detail: sintomas[1] },
  { label: 'Mesma área geográfica', met: area[0], detail: area[1] },
  { label: 'Período próximo', met: periodo[0], detail: periodo[1] },
  { label: 'Fontes independentes', met: fontes[0], detail: fontes[1] },
]

const SIGNAL_SEEDS: SignalSeed[] = [
  {
    id: '3f8a2c1e-6b4d-4e9a-9c7f-1d2e3a4b0042',
    code: 'VBE-2026-0042',
    title: 'Síndrome febril com exantema em Manaus',
    subtitle: 'Sinal consolidado a partir de quatro registros sintéticos',
    condition: 'Sarampo ou síndrome compatível',
    symptoms: ['Febre', 'Manchas vermelhas', 'Tosse'],
    neighborhood: 'Cidade Nova',
    periodStart: '2026-10-05T08:00:00-04:00',
    periodEnd: '2026-10-07T12:00:00-04:00',
    magnitude: '12–18 pessoas',
    priority: 'atencao',
    priorityRationale:
      'Três fontes independentes descrevem sintomas compatíveis na mesma área em 48 horas. A magnitude mencionada diverge entre as fontes.',
    state: 'triagem',
    createdAt: '2026-10-07T09:41:00-04:00',
    updatedAt: '2026-10-07T14:14:00-04:00',
    criteria: criteria(
      [true, 'Febre e exantema citados em 3 de 3 registros centrais'],
      [true, 'Todos os registros citam Cidade Nova, zona Norte'],
      [true, 'Menções entre 5 e 7 out., janela de 48 h'],
      [true, '2 veículos de mídia e 2 canais comunitários distintos'],
    ),
    divergences: ['Quantidade mencionada diferente entre as fontes: 12 pessoas na notícia local, cerca de 18 no relato comunitário.'],
    sources: [
      {
        id: 'a1c4e7f0-2b3d-4c5e-8f90-0042000000a1',
        code: 'REG-88213',
        type: 'midia',
        subtype: 'Notícia local',
        title: 'Unidade relata aumento de casos com febre e exantema',
        excerpt:
          'Profissionais de uma unidade básica da Cidade Nova relatam aumento de atendimentos de crianças com febre e manchas pelo corpo desde o fim de semana.',
        origin: 'Portal sintético Diário do Norte AM',
        publishedAt: '2026-10-05T19:20:00-04:00',
        neighborhood: 'Cidade Nova',
        relation: {
          kind: 'corroboracao',
          label: 'Corroboração sugerida',
          confidence: 0.88,
          rationale: 'Sintomas, área e período coincidem com o relato comunitário.',
        },
        sheet: {
          condition: 'Síndrome febril exantemática',
          symptoms: ['Febre', 'Manchas vermelhas'],
          location: 'Manaus, Cidade Nova',
          period: '4–5 out. 2026',
          magnitude: '12 pessoas',
          missingFields: ['Faixa etária', 'Situação vacinal'],
        },
      },
      {
        id: 'b2d5f8a1-3c4e-4d6f-9a01-0042000000b2',
        code: 'REG-88240',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Moradores descrevem febre e manchas vermelhas',
        excerpt:
          'Em canal de moradores, participantes comentam que várias famílias da mesma rua têm pessoas com febre, tosse e manchas vermelhas.',
        origin: 'Canal comunitário sintético Rede Bairro Norte',
        publishedAt: '2026-10-06T10:05:00-04:00',
        neighborhood: 'Cidade Nova',
        relation: {
          kind: 'corroboracao',
          label: 'Corroboração sugerida',
          confidence: 0.88,
          rationale: 'Descrição de sintomas e localização compatíveis com a notícia local.',
        },
        sheet: {
          condition: null,
          symptoms: ['Febre', 'Manchas vermelhas', 'Tosse'],
          location: 'Manaus, Cidade Nova',
          period: '5–6 out. 2026',
          magnitude: 'Cerca de 18 pessoas',
          missingFields: ['Condição mencionada', 'Fonte primária identificável'],
        },
      },
      {
        id: 'c3e6a9b2-4d5f-4e70-8b12-0042000000c3',
        code: 'REG-88302',
        type: 'midia',
        subtype: 'Atualização de mídia',
        title: 'Secretaria investiga casos no bairro',
        excerpt:
          'Reportagem informa que a vigilância municipal acompanha atendimentos com febre e exantema na Cidade Nova, sem informar número atualizado.',
        origin: 'Rádio sintética Onda Rio Negro',
        publishedAt: '2026-10-07T08:30:00-04:00',
        neighborhood: 'Cidade Nova',
        relation: {
          kind: 'atualizacao',
          label: 'Atualização sugerida',
          confidence: 0.81,
          rationale: 'Retoma o mesmo evento descrito na notícia local, com data posterior.',
        },
        sheet: {
          condition: 'Sarampo mencionado como hipótese',
          symptoms: ['Febre', 'Exantema'],
          location: 'Manaus, Cidade Nova',
          period: '7 out. 2026',
          magnitude: null,
          missingFields: ['Magnitude', 'Período de início'],
        },
      },
      {
        id: 'd4f7b0c3-5e60-4f81-9c23-0042000000d4',
        code: 'REG-88317',
        type: 'comunidade',
        subtype: 'Campanha preventiva',
        title: 'Mensagem sobre campanha de vacinação no bairro',
        excerpt:
          'Mensagem compartilhada por liderança local divulga horários de vacinação de rotina na unidade de saúde da Cidade Nova.',
        origin: 'Grupo comunitário sintético Associação Cidade Nova',
        publishedAt: '2026-10-07T11:10:00-04:00',
        neighborhood: 'Cidade Nova',
        isContext: true,
        relation: {
          kind: 'contexto',
          label: 'Contexto, não evidência central',
          confidence: 0.42,
          rationale: 'Mesma área, mas não descreve pessoas com sintomas.',
        },
        sheet: {
          condition: null,
          symptoms: [],
          location: 'Manaus, Cidade Nova',
          period: '7 out. 2026',
          magnitude: null,
          missingFields: ['Condição mencionada', 'Sintomas', 'Magnitude'],
        },
      },
    ],
  },
  {
    id: '5a1b2c3d-7e8f-4a90-8b1c-2d3e4f5a0041',
    code: 'VBE-2026-0041',
    title: 'Aumento de menções a dengue na Compensa',
    subtitle: 'Sinal consolidado a partir de três registros sintéticos',
    condition: 'Dengue',
    symptoms: ['Febre', 'Dor no corpo', 'Dor atrás dos olhos'],
    neighborhood: 'Compensa',
    periodStart: '2026-10-03T08:00:00-04:00',
    periodEnd: '2026-10-06T18:00:00-04:00',
    magnitude: 'Mais de 30 pessoas',
    priority: 'urgente',
    priorityRationale: 'Magnitude elevada e crescente citada por duas fontes de mídia independentes.',
    state: 'verificacao',
    createdAt: '2026-10-06T16:02:00-04:00',
    updatedAt: '2026-10-07T13:50:00-04:00',
    criteria: criteria(
      [true, 'Sintomas típicos de arbovirose em todos os registros'],
      [true, 'Compensa citada nos três registros'],
      [true, 'Janela de quatro dias'],
      [true, 'Dois veículos e um canal comunitário'],
    ),
    divergences: [],
    sources: [
      {
        id: 'e5a8c1d4-6f71-4a92-8d34-0041000000e5',
        code: 'REG-88104',
        type: 'midia',
        subtype: 'Notícia local',
        title: 'Moradores relatam muitos casos de dengue na Compensa',
        excerpt: 'Reportagem cita fila em unidade de pronto atendimento com pessoas relatando febre e dor no corpo.',
        origin: 'Portal sintético Amazonas Agora',
        publishedAt: '2026-10-04T18:40:00-04:00',
        neighborhood: 'Compensa',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.91, rationale: 'Mesma condição e área.' },
        sheet: { condition: 'Dengue', symptoms: ['Febre', 'Dor no corpo'], location: 'Manaus, Compensa', period: '3–4 out. 2026', magnitude: 'Mais de 30 pessoas', missingFields: ['Faixa etária'] },
      },
      {
        id: 'f6b9d2e5-7082-4ba3-9e45-0041000000f6',
        code: 'REG-88156',
        type: 'midia',
        subtype: 'Atualização de mídia',
        title: 'Ação de limpeza e recolhimento de recipientes na Compensa',
        excerpt: 'Nota menciona aumento de casos de dengue relatados por moradores e mutirão de limpeza.',
        origin: 'Rádio sintética Onda Rio Negro',
        publishedAt: '2026-10-06T09:15:00-04:00',
        neighborhood: 'Compensa',
        relation: { kind: 'atualizacao', label: 'Atualização sugerida', confidence: 0.79, rationale: 'Retoma o mesmo evento.' },
        sheet: { condition: 'Dengue', symptoms: [], location: 'Manaus, Compensa', period: '6 out. 2026', magnitude: null, missingFields: ['Sintomas', 'Magnitude'] },
      },
      {
        id: '07cae3f6-8193-4cb4-8f56-004100000007',
        code: 'REG-88171',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Vizinhos com febre alta e dor atrás dos olhos',
        excerpt: 'Participante relata que três vizinhos da mesma quadra estão com febre alta e dor atrás dos olhos.',
        origin: 'Canal comunitário sintético Compensa Unida',
        publishedAt: '2026-10-06T17:55:00-04:00',
        neighborhood: 'Compensa',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.84, rationale: 'Sintomas compatíveis na mesma área.' },
        sheet: { condition: null, symptoms: ['Febre', 'Dor atrás dos olhos'], location: 'Manaus, Compensa', period: '6 out. 2026', magnitude: '3 pessoas', missingFields: ['Condição mencionada'] },
      },
    ],
  },
  {
    id: '6b2c3d4e-8f90-4ba1-9c2d-3e4f5a6b0040',
    code: 'VBE-2026-0040',
    title: 'Síndrome respiratória em escola de Flores',
    subtitle: 'Sinal consolidado a partir de três registros sintéticos',
    condition: 'Síndrome respiratória aguda',
    symptoms: ['Tosse', 'Febre', 'Dor de garganta'],
    neighborhood: 'Flores',
    periodStart: '2026-10-06T07:00:00-04:00',
    periodEnd: '2026-10-07T10:00:00-04:00',
    magnitude: 'Cerca de 20 estudantes',
    priority: 'atencao',
    priorityRationale: 'Agrupamento em ambiente escolar, citado por relatos comunitários e uma nota de mídia.',
    state: 'triagem',
    createdAt: '2026-10-07T10:20:00-04:00',
    updatedAt: '2026-10-07T13:41:00-04:00',
    criteria: criteria(
      [true, 'Tosse e febre em todos os registros'],
      [true, 'Mesma escola citada'],
      [true, 'Menções em 24 h'],
      [true, 'Uma fonte de mídia e dois canais comunitários'],
    ),
    divergences: [],
    sources: [
      {
        id: '18dbf407-92a4-4dc5-8067-004000000018',
        code: 'REG-88266',
        type: 'midia',
        subtype: 'Notícia local',
        title: 'Escola registra faltas por sintomas gripais',
        excerpt: 'Direção de escola estadual em Flores informa aumento de faltas por tosse e febre.',
        origin: 'Portal sintético Diário do Norte AM',
        publishedAt: '2026-10-06T16:30:00-04:00',
        neighborhood: 'Flores',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.86, rationale: 'Mesmo local e sintomas.' },
        sheet: { condition: 'Síndrome gripal', symptoms: ['Tosse', 'Febre'], location: 'Manaus, Flores', period: '6 out. 2026', magnitude: 'Cerca de 20 estudantes', missingFields: ['Faixa etária'] },
      },
      {
        id: '29ec0518-a3b5-4ed6-9178-004000000029',
        code: 'REG-88279',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Pais comentam turmas com muitas crianças doentes',
        excerpt: 'Responsáveis relatam crianças com tosse e dor de garganta em duas turmas.',
        origin: 'Grupo comunitário sintético Pais de Flores',
        publishedAt: '2026-10-06T20:10:00-04:00',
        neighborhood: 'Flores',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.8, rationale: 'Sintomas compatíveis.' },
        sheet: { condition: null, symptoms: ['Tosse', 'Dor de garganta'], location: 'Manaus, Flores', period: '6 out. 2026', magnitude: null, missingFields: ['Condição mencionada', 'Magnitude'] },
      },
      {
        id: '3afd1629-b4c6-4fe7-8289-00400000003a',
        code: 'REG-88290',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Professora relata sala quase vazia',
        excerpt: 'Relato informa que muitos estudantes faltaram com febre nesta manhã.',
        origin: 'Canal comunitário sintético Rede Bairro Centro-Sul',
        publishedAt: '2026-10-07T09:00:00-04:00',
        neighborhood: 'Flores',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.74, rationale: 'Mesma escola, data seguinte.' },
        sheet: { condition: null, symptoms: ['Febre'], location: 'Manaus, Flores', period: '7 out. 2026', magnitude: null, missingFields: ['Condição mencionada', 'Magnitude'] },
      },
    ],
  },
  {
    id: '7c3d4e5f-90a1-4cb2-8d3e-4f5a6b7c0039',
    code: 'VBE-2026-0039',
    title: 'Gastroenterite após evento no Centro',
    subtitle: 'Sinal consolidado a partir de dois registros sintéticos',
    condition: 'Gastroenterite aguda',
    symptoms: ['Diarreia', 'Vômito', 'Dor abdominal'],
    neighborhood: 'Centro',
    periodStart: '2026-10-05T12:00:00-04:00',
    periodEnd: '2026-10-06T12:00:00-04:00',
    magnitude: '8 pessoas',
    priority: 'monitorar',
    priorityRationale: 'Duas fontes e magnitude baixa associadas a um evento pontual.',
    state: 'triagem',
    createdAt: '2026-10-06T14:30:00-04:00',
    updatedAt: '2026-10-07T11:02:00-04:00',
    criteria: criteria(
      [true, 'Sintomas gastrointestinais nos dois registros'],
      [true, 'Mesmo evento no Centro'],
      [true, 'Menções em 24 h'],
      [true, 'Uma fonte de mídia e uma comunitária'],
    ),
    divergences: [],
    sources: [
      {
        id: '4b0e273a-c5d7-4008-939a-00390000004b',
        code: 'REG-88188',
        type: 'midia',
        subtype: 'Notícia local',
        title: 'Participantes passam mal após festa no Centro',
        excerpt: 'Nota cita pessoas com vômito e diarreia após confraternização em espaço de eventos.',
        origin: 'Portal sintético Amazonas Agora',
        publishedAt: '2026-10-05T21:00:00-04:00',
        neighborhood: 'Centro',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.83, rationale: 'Mesmo evento e sintomas.' },
        sheet: { condition: 'Intoxicação alimentar', symptoms: ['Vômito', 'Diarreia'], location: 'Manaus, Centro', period: '5 out. 2026', magnitude: '8 pessoas', missingFields: ['Alimento suspeito'] },
      },
      {
        id: '5c1f384b-d6e8-4119-84ab-00390000005c',
        code: 'REG-88199',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Convidados relatam dor de barriga',
        excerpt: 'Participante comenta que vários convidados tiveram dor abdominal no dia seguinte.',
        origin: 'Canal comunitário sintético Centro Histórico Vivo',
        publishedAt: '2026-10-06T10:30:00-04:00',
        neighborhood: 'Centro',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.77, rationale: 'Mesmo evento.' },
        sheet: { condition: null, symptoms: ['Dor abdominal'], location: 'Manaus, Centro', period: '6 out. 2026', magnitude: null, missingFields: ['Condição mencionada', 'Magnitude'] },
      },
    ],
  },
  {
    id: '8d4e5f6a-a1b2-4dc3-9e4f-5a6b7c8d0038',
    code: 'VBE-2026-0038',
    title: 'Possível leptospirose após alagamento no Jorge Teixeira',
    subtitle: 'Sinal consolidado a partir de quatro registros sintéticos',
    condition: 'Leptospirose',
    symptoms: ['Febre', 'Dor na panturrilha', 'Olhos amarelados'],
    neighborhood: 'Jorge Teixeira',
    periodStart: '2026-09-30T08:00:00-04:00',
    periodEnd: '2026-10-06T18:00:00-04:00',
    magnitude: '5–7 pessoas',
    priority: 'urgente',
    priorityRationale: 'Condição de alto impacto mencionada após alagamento, com fontes independentes.',
    state: 'avaliacao_risco',
    createdAt: '2026-10-04T08:15:00-04:00',
    updatedAt: '2026-10-07T12:10:00-04:00',
    criteria: criteria(
      [true, 'Febre e dor muscular nos quatro registros'],
      [true, 'Área alagada do Jorge Teixeira'],
      [true, 'Até sete dias após alagamento'],
      [true, 'Dois veículos e dois canais comunitários'],
    ),
    divergences: [],
    sources: [
      {
        id: '6d20495c-e7f9-422a-95bc-00380000006d',
        code: 'REG-87990',
        type: 'midia',
        subtype: 'Notícia local',
        title: 'Moradores enfrentam alagamento após chuva forte',
        excerpt: 'Reportagem sobre ruas alagadas por dois dias no Jorge Teixeira.',
        origin: 'Portal sintético Diário do Norte AM',
        publishedAt: '2026-09-30T18:00:00-04:00',
        neighborhood: 'Jorge Teixeira',
        relation: { kind: 'contexto', label: 'Contexto, não evidência central', confidence: 0.55, rationale: 'Descreve exposição, não pessoas com sintomas.' },
        sheet: { condition: null, symptoms: [], location: 'Manaus, Jorge Teixeira', period: '29–30 set. 2026', magnitude: null, missingFields: ['Condição mencionada', 'Sintomas', 'Magnitude'] },
        isContext: true,
      },
      {
        id: '7e315a6d-f80a-433b-86cd-00380000007e',
        code: 'REG-88051',
        type: 'midia',
        subtype: 'Atualização de mídia',
        title: 'Pessoas com febre e dor muscular após enchente',
        excerpt: 'Reportagem cita moradores atendidos com febre e dor na panturrilha.',
        origin: 'Rádio sintética Onda Rio Negro',
        publishedAt: '2026-10-03T12:30:00-04:00',
        neighborhood: 'Jorge Teixeira',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.87, rationale: 'Sintomas compatíveis após exposição.' },
        sheet: { condition: 'Leptospirose mencionada como hipótese', symptoms: ['Febre', 'Dor na panturrilha'], location: 'Manaus, Jorge Teixeira', period: '2–3 out. 2026', magnitude: '5 pessoas', missingFields: [] },
      },
      {
        id: '8f426b7e-091b-444c-97de-00380000008f',
        code: 'REG-88077',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Vizinho com olhos amarelados',
        excerpt: 'Relato de morador com febre e olhos amarelados após limpar a casa alagada.',
        origin: 'Canal comunitário sintético Leste Conectado',
        publishedAt: '2026-10-04T07:40:00-04:00',
        neighborhood: 'Jorge Teixeira',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.82, rationale: 'Sintomas compatíveis.' },
        sheet: { condition: null, symptoms: ['Febre', 'Olhos amarelados'], location: 'Manaus, Jorge Teixeira', period: '3–4 out. 2026', magnitude: '1 pessoa', missingFields: ['Condição mencionada'] },
      },
      {
        id: '90537c8f-1a2c-455d-88ef-003800000090',
        code: 'REG-88140',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Família inteira com febre na mesma rua',
        excerpt: 'Participantes relatam febre e dor muscular em uma família e dois vizinhos.',
        origin: 'Canal comunitário sintético Leste Conectado',
        publishedAt: '2026-10-06T15:20:00-04:00',
        neighborhood: 'Jorge Teixeira',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.78, rationale: 'Mesma área e sintomas.' },
        sheet: { condition: null, symptoms: ['Febre', 'Dor muscular'], location: 'Manaus, Jorge Teixeira', period: '5–6 out. 2026', magnitude: '7 pessoas', missingFields: ['Condição mencionada'] },
      },
    ],
  },
  {
    id: '9e5f6a7b-b2c3-4ed4-8f5a-6b7c8d9e0037',
    code: 'VBE-2026-0037',
    title: 'Campanha de vacinação contra influenza na Cidade Nova',
    subtitle: 'Registro mantido como contexto',
    condition: 'Sem condição associada',
    symptoms: [],
    neighborhood: 'Cidade Nova',
    periodStart: '2026-10-07T08:00:00-04:00',
    periodEnd: '2026-10-07T08:00:00-04:00',
    magnitude: null,
    priority: 'contexto',
    priorityRationale: 'Comunicado preventivo sem menção a pessoas com sintomas. Sugere-se manter como contexto.',
    state: 'triagem',
    createdAt: '2026-10-07T08:40:00-04:00',
    updatedAt: '2026-10-07T09:05:00-04:00',
    flag: 'contexto',
    criteria: criteria(
      [false, 'Nenhum sintoma mencionado'],
      [true, 'Cidade Nova'],
      [true, 'Mesma data de outros sinais na área'],
      [false, 'Fonte única'],
    ),
    divergences: [],
    sources: [
      {
        id: 'a1648d90-2b3d-466e-990f-0037000000a1',
        code: 'REG-88295',
        type: 'midia',
        subtype: 'Campanha preventiva',
        title: 'Unidades ampliam horário de vacinação',
        excerpt: 'Nota informa ampliação de horário de vacinação contra influenza em unidades da zona Norte.',
        origin: 'Portal sintético Amazonas Agora',
        publishedAt: '2026-10-07T07:50:00-04:00',
        neighborhood: 'Cidade Nova',
        isContext: true,
        relation: { kind: 'contexto', label: 'Contexto, não evidência central', confidence: 0.35, rationale: 'Comunicado preventivo.' },
        sheet: { condition: null, symptoms: [], location: 'Manaus, zona Norte', period: '7 out. 2026', magnitude: null, missingFields: ['Condição mencionada', 'Sintomas', 'Magnitude'] },
      },
    ],
  },
  {
    id: 'af6a7b8c-c3d4-4fe5-9a6b-7c8d9eaf0036',
    code: 'VBE-2026-0036',
    title: 'Quadro febril não especificado no Distrito Industrial',
    subtitle: 'Sinal consolidado a partir de dois registros sintéticos',
    condition: 'Não identificada',
    symptoms: ['Febre', 'Fraqueza', 'Dor de cabeça'],
    neighborhood: 'Distrito Industrial',
    periodStart: '2026-10-04T06:00:00-04:00',
    periodEnd: '2026-10-06T22:00:00-04:00',
    magnitude: 'Vários trabalhadores',
    priority: 'atencao',
    priorityRationale: 'Condição não identificada em ambiente de trabalho coletivo; apenas fontes comunitárias.',
    state: 'triagem',
    createdAt: '2026-10-07T07:10:00-04:00',
    updatedAt: '2026-10-07T10:48:00-04:00',
    flag: 'condicao_desconhecida',
    criteria: criteria(
      [true, 'Febre e fraqueza nos dois registros'],
      [true, 'Mesmo polo industrial'],
      [true, 'Janela de três dias'],
      [false, 'Os dois relatos podem ter a mesma origem'],
    ),
    divergences: ['Independência entre as fontes não confirmada.'],
    sources: [
      {
        id: 'b2759ea1-3c4e-477f-8a10-0036000000b2',
        code: 'REG-88232',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Trabalhadores afastados com febre',
        excerpt: 'Relato menciona vários trabalhadores de um mesmo turno afastados com febre e fraqueza.',
        origin: 'Canal comunitário sintético Trabalhadores do Polo',
        publishedAt: '2026-10-05T22:15:00-04:00',
        neighborhood: 'Distrito Industrial',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.69, rationale: 'Sintomas e local compatíveis.' },
        sheet: { condition: null, symptoms: ['Febre', 'Fraqueza'], location: 'Manaus, Distrito Industrial', period: '4–5 out. 2026', magnitude: 'Vários trabalhadores', missingFields: ['Condição mencionada', 'Magnitude numérica'] },
      },
      {
        id: 'c386afb2-4d5f-4880-9b21-0036000000c3',
        code: 'REG-88251',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Colegas com dor de cabeça forte',
        excerpt: 'Participante relata colegas com dor de cabeça forte e febre, sem diagnóstico informado.',
        origin: 'Canal comunitário sintético Trabalhadores do Polo',
        publishedAt: '2026-10-06T21:40:00-04:00',
        neighborhood: 'Distrito Industrial',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.64, rationale: 'Mesmo canal e local.' },
        sheet: { condition: null, symptoms: ['Febre', 'Dor de cabeça'], location: 'Manaus, Distrito Industrial', period: '6 out. 2026', magnitude: null, missingFields: ['Condição mencionada', 'Magnitude'] },
      },
    ],
  },
  {
    id: 'b07b8c9d-d4e5-4af6-8b7c-8d9eafb00035',
    code: 'VBE-2026-0035',
    title: 'Síndrome diarreica com localização divergente',
    subtitle: 'Sinal consolidado a partir de três registros sintéticos',
    condition: 'Síndrome diarreica aguda',
    symptoms: ['Diarreia', 'Febre baixa'],
    neighborhood: 'Compensa',
    periodStart: '2026-10-02T08:00:00-04:00',
    periodEnd: '2026-10-05T18:00:00-04:00',
    magnitude: '10–15 pessoas',
    priority: 'monitorar',
    priorityRationale: 'Fontes concordam sobre sintomas, mas divergem sobre o bairro. Conferir local antes de priorizar.',
    state: 'verificacao',
    createdAt: '2026-10-05T19:30:00-04:00',
    updatedAt: '2026-10-07T08:20:00-04:00',
    flag: 'conflito_geografico',
    criteria: criteria(
      [true, 'Diarreia nos três registros'],
      [false, 'Compensa em dois registros, Centro em um'],
      [true, 'Janela de quatro dias'],
      [true, 'Duas fontes de mídia e uma comunitária'],
    ),
    divergences: ['Bairro divergente: Compensa em dois registros, Centro em um.'],
    sources: [
      {
        id: 'd497b0c3-5e60-4991-8c32-0035000000d4',
        code: 'REG-88012',
        type: 'midia',
        subtype: 'Notícia local',
        title: 'Moradores reclamam de água turva',
        excerpt: 'Moradores da Compensa relatam água turva e casos de diarreia em crianças.',
        origin: 'Portal sintético Amazonas Agora',
        publishedAt: '2026-10-02T17:10:00-04:00',
        neighborhood: 'Compensa',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.76, rationale: 'Sintomas compatíveis.' },
        sheet: { condition: null, symptoms: ['Diarreia'], location: 'Manaus, Compensa', period: '2 out. 2026', magnitude: '10 pessoas', missingFields: ['Condição mencionada'] },
      },
      {
        id: 'e5a8c1d4-6f71-4aa2-9d43-0035000000e5',
        code: 'REG-88066',
        type: 'midia',
        subtype: 'Atualização de mídia',
        title: 'Abastecimento é normalizado após reparo',
        excerpt: 'Nota sobre reparo em rede de abastecimento cita casos de diarreia no Centro.',
        origin: 'Rádio sintética Onda Rio Negro',
        publishedAt: '2026-10-04T09:00:00-04:00',
        neighborhood: 'Centro',
        relation: { kind: 'divergencia', label: 'Divergência sugerida', confidence: 0.58, rationale: 'Mesmos sintomas, bairro diferente.' },
        sheet: { condition: null, symptoms: ['Diarreia'], location: 'Manaus, Centro', period: '3–4 out. 2026', magnitude: null, missingFields: ['Condição mencionada', 'Magnitude'] },
      },
      {
        id: 'f6b9d2e5-7082-4bb3-8e54-0035000000f6',
        code: 'REG-88093',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Crianças com diarreia na mesma rua',
        excerpt: 'Relato de mães sobre crianças com diarreia e febre baixa.',
        origin: 'Canal comunitário sintético Compensa Unida',
        publishedAt: '2026-10-05T11:45:00-04:00',
        neighborhood: 'Compensa',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.8, rationale: 'Mesma área e sintomas.' },
        sheet: { condition: null, symptoms: ['Diarreia', 'Febre baixa'], location: 'Manaus, Compensa', period: '4–5 out. 2026', magnitude: '15 pessoas', missingFields: ['Condição mencionada'] },
      },
    ],
  },
  {
    id: 'c18c9dae-e5f6-4b07-9c8d-9eafb0c10034',
    code: 'VBE-2026-0034',
    title: 'Menções a dengue com sinais de alarme no Jorge Teixeira',
    subtitle: 'Sinal consolidado a partir de dois registros sintéticos',
    condition: 'Dengue',
    symptoms: ['Febre', 'Dor abdominal intensa', 'Sangramento gengival'],
    neighborhood: 'Jorge Teixeira',
    periodStart: '2026-10-01T08:00:00-04:00',
    periodEnd: '2026-10-04T20:00:00-04:00',
    magnitude: '3 pessoas',
    priority: 'atencao',
    priorityRationale: 'Sinais de alarme mencionados, magnitude baixa, duas fontes.',
    state: 'avaliacao_risco',
    createdAt: '2026-10-04T21:00:00-04:00',
    updatedAt: '2026-10-06T17:30:00-04:00',
    criteria: criteria(
      [true, 'Febre e sinais de alarme'],
      [true, 'Jorge Teixeira'],
      [true, 'Janela de quatro dias'],
      [true, 'Uma fonte de mídia e uma comunitária'],
    ),
    divergences: [],
    sources: [
      {
        id: '07cae3f6-8193-4cc4-9f65-003400000007',
        code: 'REG-87975',
        type: 'midia',
        subtype: 'Notícia local',
        title: 'Pacientes com dengue procuram atendimento',
        excerpt: 'Nota cita pacientes com dor abdominal intensa e sangramento gengival.',
        origin: 'Portal sintético Diário do Norte AM',
        publishedAt: '2026-10-02T19:30:00-04:00',
        neighborhood: 'Jorge Teixeira',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.85, rationale: 'Mesma condição e área.' },
        sheet: { condition: 'Dengue', symptoms: ['Dor abdominal intensa', 'Sangramento gengival'], location: 'Manaus, Jorge Teixeira', period: '1–2 out. 2026', magnitude: '3 pessoas', missingFields: [] },
      },
      {
        id: '18dbf407-92a4-4dd5-8076-003400000018',
        code: 'REG-88020',
        type: 'comunidade',
        subtype: 'Relato comunitário',
        title: 'Moradora relata internação de vizinho',
        excerpt: 'Relato sobre vizinho internado após febre e sangramento.',
        origin: 'Canal comunitário sintético Leste Conectado',
        publishedAt: '2026-10-04T08:20:00-04:00',
        neighborhood: 'Jorge Teixeira',
        relation: { kind: 'corroboracao', label: 'Corroboração sugerida', confidence: 0.72, rationale: 'Sintomas compatíveis.' },
        sheet: { condition: null, symptoms: ['Febre', 'Sangramento'], location: 'Manaus, Jorge Teixeira', period: '3–4 out. 2026', magnitude: '1 pessoa', missingFields: ['Condição mencionada'] },
      },
    ],
  },
]

export const SOURCES: SourceRecord[] = SIGNAL_SEEDS.flatMap((signal) =>
  signal.sources.map((seed) => ({
    id: seed.id,
    code: seed.code,
    signalId: signal.id,
    type: seed.type,
    subtype: seed.subtype,
    title: seed.title,
    excerpt: seed.excerpt,
    origin: seed.origin,
    publishedAt: seed.publishedAt,
    municipality: MUNICIPALITY,
    neighborhood: seed.neighborhood,
    isContext: seed.isContext ?? false,
    relation: seed.relation,
    sheet: sheetFrom(seed),
  })),
)

export const SIGNALS: Signal[] = SIGNAL_SEEDS.map(({ sources, ...signal }) => ({
  ...signal,
  slug: signal.code.toLowerCase(),
  municipality: MUNICIPALITY,
  sourceIds: sources.map((s) => s.id),
}))

export function getSignalBySlug(slug: string) {
  return SIGNALS.find((s) => s.slug === slug.toLowerCase())
}

export function getSourcesForSignal(signalId: string) {
  return SOURCES.filter((s) => s.signalId === signalId)
}

export function countSourcesByType(signal: Signal) {
  const sources = getSourcesForSignal(signal.id)
  return {
    midia: sources.filter((s) => s.type === 'midia').length,
    comunidade: sources.filter((s) => s.type === 'comunidade').length,
  }
}

export function buildAuditTrail(signal: Signal): AuditEvent[] {
  const created = new Date(signal.createdAt).getTime()
  const at = (minutes: number) => new Date(created + minutes * 60000).toISOString()
  const sourceCount = signal.sourceIds.length
  return [
    {
      id: `${signal.id}-evt-1`,
      signalId: signal.id,
      at: at(0),
      actor: 'sistema',
      title: 'Sinal criado',
      description: `${sourceCount} registros recebidos e extraídos com ${EXTRACTION_VERSION}.`,
    },
    {
      id: `${signal.id}-evt-2`,
      signalId: signal.id,
      at: at(2),
      actor: 'sistema',
      title: 'Agrupamento sugerido',
      description: 'Registros aproximados por sintomas, área geográfica e período.',
    },
    {
      id: `${signal.id}-evt-3`,
      signalId: signal.id,
      at: at(3),
      actor: 'sistema',
      title: 'Prioridade calculada',
      description: 'Prioridade sugerida a partir de fontes, magnitude e condição mencionada.',
    },
    {
      id: `${signal.id}-evt-4`,
      signalId: signal.id,
      at: signal.updatedAt,
      actor: 'sistema',
      title: 'Aguardando revisão',
      description: 'Sinal disponível na fila de triagem para decisão da vigilância.',
    },
  ]
}

export const QUEUE_INDICATORS: QueueIndicator[] = [
  { key: 'triagem', label: 'Aguardando triagem', value: 18, trend: 'up', trendLabel: '+4 desde ontem' },
  { key: 'verificacao', label: 'Em verificação', value: 6, trend: 'flat', trendLabel: 'Estável' },
  { key: 'avaliacao_risco', label: 'Em avaliação de risco', value: 3, trend: 'up', trendLabel: '+1 desde ontem' },
  { key: 'conflito', label: 'Com evidência conflitante', value: 2, trend: 'down', trendLabel: '−1 desde ontem' },
]

export const NEIGHBORHOODS: NeighborhoodSummary[] = [
  {
    id: 'cidade-nova',
    name: 'Cidade Nova',
    x: 560,
    y: 150,
    signals: 8,
    media: 11,
    community: 9,
    conditions: [
      { label: 'Síndrome febril exantemática', count: 3 },
      { label: 'Síndrome respiratória', count: 2 },
      { label: 'Contexto preventivo', count: 2 },
    ],
    states: [
      { state: 'triagem', count: 6 },
      { state: 'verificacao', count: 2 },
    ],
    dominantState: 'triagem',
  },
  {
    id: 'compensa',
    name: 'Compensa',
    x: 190,
    y: 330,
    signals: 5,
    media: 7,
    community: 4,
    conditions: [
      { label: 'Dengue', count: 3 },
      { label: 'Síndrome diarreica', count: 2 },
    ],
    states: [
      { state: 'triagem', count: 2 },
      { state: 'verificacao', count: 3 },
    ],
    dominantState: 'verificacao',
  },
  {
    id: 'flores',
    name: 'Flores',
    x: 430,
    y: 230,
    signals: 4,
    media: 3,
    community: 5,
    conditions: [
      { label: 'Síndrome respiratória', count: 3 },
      { label: 'Dengue', count: 1 },
    ],
    states: [{ state: 'triagem', count: 4 }],
    dominantState: 'triagem',
  },
  {
    id: 'centro',
    name: 'Centro',
    x: 360,
    y: 410,
    signals: 4,
    media: 5,
    community: 3,
    conditions: [
      { label: 'Gastroenterite', count: 2 },
      { label: 'Síndrome diarreica', count: 2 },
    ],
    states: [
      { state: 'triagem', count: 3 },
      { state: 'encerrado', count: 1 },
    ],
    dominantState: 'triagem',
  },
  {
    id: 'jorge-teixeira',
    name: 'Jorge Teixeira',
    x: 760,
    y: 240,
    signals: 6,
    media: 6,
    community: 8,
    conditions: [
      { label: 'Leptospirose', count: 3 },
      { label: 'Dengue', count: 3 },
    ],
    states: [
      { state: 'triagem', count: 2 },
      { state: 'verificacao', count: 1 },
      { state: 'avaliacao_risco', count: 3 },
    ],
    dominantState: 'avaliacao_risco',
  },
  {
    id: 'distrito-industrial',
    name: 'Distrito Industrial',
    x: 620,
    y: 400,
    signals: 2,
    media: 0,
    community: 4,
    conditions: [{ label: 'Condição não identificada', count: 2 }],
    states: [{ state: 'triagem', count: 2 }],
    dominantState: 'triagem',
  },
]

export const PANORAMA_TOTALS = {
  periodLabel: '24 set.–7 out. 2026',
  signals: 29,
  awaitingTriage: 18,
  multiSource: 11,
  divergent: 3,
}

export const TOP_CONDITIONS = [
  { label: 'Dengue', count: 7 },
  { label: 'Síndrome respiratória', count: 5 },
  { label: 'Síndrome diarreica / gastroenterite', count: 4 },
  { label: 'Síndrome febril exantemática', count: 3 },
  { label: 'Leptospirose', count: 3 },
]

export interface DailyPoint {
  date: string
  label: string
  sinais: number
  midia: number
  comunidade: number
}

const DAILY_RAW: [number, number, number][] = [
  [1, 3, 1], [0, 2, 1], [1, 2, 2], [2, 4, 2], [1, 3, 1], [0, 1, 1], [1, 2, 3],
  [2, 5, 3], [1, 3, 2], [3, 6, 4], [2, 4, 4], [4, 7, 5], [5, 8, 6], [6, 9, 7],
  [3, 6, 4], [2, 5, 3], [1, 3, 2], [2, 4, 3], [3, 5, 4], [1, 2, 2], [2, 4, 3],
  [1, 3, 2], [3, 5, 4], [2, 4, 3], [4, 7, 5], [3, 6, 4], [5, 8, 6], [4, 7, 6],
  [6, 9, 8], [3, 5, 5],
]

export const DAILY_SERIES: DailyPoint[] = DAILY_RAW.map(([sinais, midia, comunidade], index) => {
  const date = new Date(Date.UTC(2026, 8, 8 + index, 12))
  const day = date.getUTCDate()
  const month = date.getUTCMonth() === 8 ? 'set.' : 'out.'
  return {
    date: date.toISOString().slice(0, 10),
    label: `${day} ${month}`,
    sinais,
    midia,
    comunidade,
  }
})

export const PIPELINE_FUNNEL = [
  { label: 'Registros recebidos', value: 120 },
  { label: 'Pares candidatos', value: 48 },
  { label: 'Sinais consolidados', value: 29 },
  { label: 'Revisados', value: 12 },
]

export const PIPELINE_QUALITY: PipelineMetric[] = [
  { key: 'processados', label: 'Processados', value: '98%', description: '118 de 120 registros extraídos sem erro' },
  { key: 'falha', label: 'Com falha', value: '2%', description: '2 registros com texto ilegível', tone: 'erro' },
  { key: 'mediana', label: 'Tempo mediano', value: '4 min 12 s', description: 'Da coleta à disponibilização na fila' },
  { key: 'execucao', label: 'Última execução', value: '14:32', description: '7 out. 2026 · lote 2026-10-07-14' },
]

export const NEIGHBORHOOD_NAMES = NEIGHBORHOODS.map((n) => n.name)
