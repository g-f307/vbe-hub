'use client'

import { Search, X } from 'lucide-react'
import { FilterSelect, type FilterOption } from '@/components/filter-select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PRIORITY_LABEL, WORKFLOW_QUEUE_LABEL } from '@/lib/labels'
import { NEIGHBORHOOD_NAMES } from '@/lib/mock-data'
import type { SuggestedPriority, WorkflowState } from '@/lib/types'
import { cn } from '@/lib/utils'

export interface QueueFilterState {
  search: string
  state: string
  priority: string
  period: string
  neighborhood: string
  sourceType: string
}

export const DEFAULT_FILTERS: QueueFilterState = {
  search: '',
  state: 'todos',
  priority: 'todas',
  period: '14d',
  neighborhood: 'todos',
  sourceType: 'todas',
}

const STATE_OPTIONS: FilterOption[] = [
  { value: 'todos', label: 'Todos os estados' },
  ...(['triagem', 'verificacao', 'avaliacao_risco', 'encerrado'] as WorkflowState[]).map((s) => ({
    value: s,
    label: WORKFLOW_QUEUE_LABEL[s],
  })),
]

const PRIORITY_OPTIONS: FilterOption[] = [
  { value: 'todas', label: 'Todas as prioridades' },
  ...(['urgente', 'atencao', 'monitorar', 'contexto'] as SuggestedPriority[]).map((p) => ({
    value: p,
    label: PRIORITY_LABEL[p],
  })),
]

const PERIOD_OPTIONS: FilterOption[] = [
  { value: '24h', label: 'Últimas 24 horas' },
  { value: '7d', label: 'Últimos 7 dias' },
  { value: '14d', label: 'Últimos 14 dias' },
]

const NEIGHBORHOOD_OPTIONS: FilterOption[] = [
  { value: 'todos', label: 'Todos os bairros' },
  ...NEIGHBORHOOD_NAMES.map((n) => ({ value: n, label: n })),
]

const SOURCE_OPTIONS: FilterOption[] = [
  { value: 'todas', label: 'Todas as fontes' },
  { value: 'midia', label: 'Com mídia' },
  { value: 'comunidade', label: 'Com comunidade' },
  { value: 'ambas', label: 'Mídia e comunidade' },
]

const OPTION_SETS: Record<keyof Omit<QueueFilterState, 'search'>, FilterOption[]> = {
  state: STATE_OPTIONS,
  priority: PRIORITY_OPTIONS,
  period: PERIOD_OPTIONS,
  neighborhood: NEIGHBORHOOD_OPTIONS,
  sourceType: SOURCE_OPTIONS,
}

export function SearchField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <Label htmlFor="busca-sinais" className="text-xs font-medium text-ardosia">
        Buscar
      </Label>
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-ardosia" aria-hidden />
        <Input
          id="busca-sinais"
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Código, condição, bairro ou sintoma"
          className="h-9 bg-mineral pl-8"
        />
      </div>
    </div>
  )
}

export function FilterControls({
  filters,
  onChange,
  layout = 'row',
}: {
  filters: QueueFilterState
  onChange: (next: QueueFilterState) => void
  layout?: 'row' | 'stack'
}) {
  const set = (key: keyof QueueFilterState) => (value: string) => onChange({ ...filters, [key]: value })
  return (
    <div
      className={cn(
        layout === 'row' ? 'grid grid-cols-5 gap-2' : 'flex flex-col gap-4',
      )}
    >
      <FilterSelect label="Estado" value={filters.state} onChange={set('state')} options={STATE_OPTIONS} />
      <FilterSelect label="Prioridade" value={filters.priority} onChange={set('priority')} options={PRIORITY_OPTIONS} />
      <FilterSelect label="Período" value={filters.period} onChange={set('period')} options={PERIOD_OPTIONS} />
      <FilterSelect label="Bairro" value={filters.neighborhood} onChange={set('neighborhood')} options={NEIGHBORHOOD_OPTIONS} />
      <FilterSelect label="Tipo de fonte" value={filters.sourceType} onChange={set('sourceType')} options={SOURCE_OPTIONS} />
    </div>
  )
}

export function activeFilterChips(filters: QueueFilterState) {
  const chips: { key: keyof QueueFilterState; label: string }[] = []
  if (filters.search.trim()) chips.push({ key: 'search', label: `“${filters.search.trim()}”` })
  ;(Object.keys(OPTION_SETS) as (keyof typeof OPTION_SETS)[]).forEach((key) => {
    if (filters[key] !== DEFAULT_FILTERS[key]) {
      const option = OPTION_SETS[key].find((o) => o.value === filters[key])
      if (option) chips.push({ key, label: option.label })
    }
  })
  return chips
}

export function ActiveFilterChips({
  filters,
  onChange,
}: {
  filters: QueueFilterState
  onChange: (next: QueueFilterState) => void
}) {
  const chips = activeFilterChips(filters)
  if (chips.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Filtros ativos">
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          onClick={() => onChange({ ...filters, [chip.key]: DEFAULT_FILTERS[chip.key] })}
          className="inline-flex h-7 items-center gap-1 rounded-sm border border-agua-strong bg-mineral px-2 text-xs text-grafite hover:border-igarape hover:text-igarape-ink"
          aria-label={`Remover filtro ${chip.label}`}
        >
          {chip.label}
          <X className="size-3" aria-hidden />
        </button>
      ))}
      <button
        type="button"
        onClick={() => onChange(DEFAULT_FILTERS)}
        className="h-7 px-1 text-xs font-medium text-igarape underline-offset-2 hover:underline"
      >
        Limpar filtros
      </button>
    </div>
  )
}
