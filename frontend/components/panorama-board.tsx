'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { ArrowRight, MapPinned, MessagesSquare, Newspaper, TriangleAlert } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { StateLabel } from '@/components/status-badges'
import { TerritoryMap } from '@/components/territory-map'
import { Button } from '@/components/ui/button'
import { formatDateTime, formatPeriod } from '@/lib/format'
import type { GeographicArea, GeographicSummary } from '@/lib/panorama-read'
import { geometryForArea } from '@/lib/territory-geometry'
import type { WorkflowState } from '@/lib/types'
import { cn } from '@/lib/utils'

const API_TO_UI_STATE: Record<string, WorkflowState> = {
  detected: 'detectado',
  triage: 'triagem',
  verification: 'verificacao',
  risk_assessment: 'avaliacao_risco',
  closed: 'encerrado',
}

export function PanoramaBoard({ summary }: { summary: GeographicSummary }) {
  const [selectedKey, setSelectedKey] = useState(summary.areas[0]?.key ?? null)
  const selected = useMemo(
    () => summary.areas.find((area) => area.key === selectedKey) ?? summary.areas[0] ?? null,
    [selectedKey, summary.areas],
  )
  const mappedAreas = useMemo(
    () => summary.areas.filter((area) => geometryForArea(area.municipality, area.district)),
    [summary.areas],
  )

  if (summary.totals.signals === 0) return <EmptyPanorama />

  const period = formatPeriod(summary.window.start, summary.window.end)
  const updated = summary.updatedAt ? `Atualizado em ${formatDateTime(summary.updatedAt)}` : 'Sem atualização registrada'

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <PageHeader
        title="Panorama territorial"
        description="Distribuição agregada dos sinais sintéticos consolidados. Apoia a triagem e não confirma eventos de saúde."
        meta={`${period} · ${updated}`}
        actions={
          <Button variant="outline" render={<Link href="/triagem" />} nativeButton={false}>
            Abrir fila <ArrowRight aria-hidden />
          </Button>
        }
      />

      <section
        aria-label="Cobertura territorial do período"
        className="grid overflow-hidden rounded-md border border-agua bg-mineral sm:grid-cols-2 xl:grid-cols-4 xl:divide-x xl:divide-agua"
      >
        <SummaryMetric value={summary.totals.signals} label="sinais no período" />
        <SummaryMetric value={summary.totals.areas} label="áreas agregadas" />
        <SummaryMetric value={summary.totals.mappedSignals} label="com área mapeável" />
        <SummaryMetric
          value={summary.totals.unmappedSignals}
          label="sem área agregável"
          attention={summary.totals.unmappedSignals > 0}
        />
      </section>

      <section aria-labelledby="territorio-titulo" className="overflow-hidden rounded-md border border-agua bg-mineral">
        <div className="flex flex-col gap-2 border-b border-agua px-4 py-3 md:flex-row md:items-center md:justify-between md:px-5">
          <div>
            <h2 id="territorio-titulo" className="text-base font-semibold text-encontro">Distribuição por território</h2>
            <p className="mt-0.5 text-sm text-ardosia">Selecione uma área no mapa ou na lista para consultar o mesmo agregado.</p>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs text-ardosia">
            <MapPinned className="size-4 text-igarape" aria-hidden /> Geometria local · demo-areas-v1
          </span>
        </div>

        <div className="grid min-h-[440px] xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
          <div className="min-h-[360px] border-b border-agua bg-nevoa xl:border-r xl:border-b-0">
            <TerritoryMap areas={mappedAreas} selectedKey={selected?.key ?? null} onSelect={setSelectedKey} />
          </div>

          <div className="flex min-w-0 flex-col">
            <div className="border-b border-agua px-4 py-3">
              <h3 className="text-sm font-semibold text-encontro">Áreas com sinais</h3>
              <p className="mt-0.5 text-xs leading-relaxed text-ardosia">Alternativa textual completa para navegação por teclado e leitor de tela.</p>
            </div>
            <ul className="max-h-64 overflow-y-auto border-b border-agua" aria-label="Lista de áreas agregadas">
              {summary.areas.map((area) => {
                const active = selected?.key === area.key
                const hasGeometry = Boolean(geometryForArea(area.municipality, area.district))
                return (
                  <li key={area.key} className="border-b border-agua last:border-b-0">
                    <button
                      type="button"
                      onClick={() => setSelectedKey(area.key)}
                      aria-pressed={active}
                      className={cn(
                        'flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-vitoria-soft focus-visible:outline-offset-[-3px]',
                        active && 'bg-vitoria-soft',
                      )}
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-grafite">{area.district}</span>
                        <span className="mt-0.5 block text-xs text-ardosia">
                          {area.municipality} · {hasGeometry ? 'No mapa' : 'Geometria indisponível'}
                        </span>
                      </span>
                      <span className="shrink-0 font-mono text-sm font-semibold text-encontro">{area.signals}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
            {selected ? <AreaDetail area={selected} /> : null}
          </div>
        </div>
      </section>

      <aside className="flex gap-3 rounded-md border border-dashed border-agua-strong bg-mineral px-4 py-3 text-sm leading-relaxed text-ardosia">
        <TriangleAlert className="mt-0.5 size-4 shrink-0 text-andiroba-ink" aria-hidden />
        <p>
          <strong className="font-semibold text-grafite">Dados sintéticos de apoio à triagem.</strong>{' '}
          Os contornos são esquemáticos e mostram somente agregados por área. Não exibem endereço, coordenada de relato ou localização individual.
        </p>
      </aside>
    </div>
  )
}

function SummaryMetric({ value, label, attention = false }: { value: number; label: string; attention?: boolean }) {
  return (
    <div className="border-b border-agua px-4 py-4 last:border-b-0 sm:nth-[odd]:border-r xl:border-b-0">
      <p className={cn('text-2xl font-semibold tracking-tight text-encontro', attention && 'text-andiroba-ink')}>{value}</p>
      <p className="mt-1 text-sm text-ardosia">{label}</p>
    </div>
  )
}

function AreaDetail({ area }: { area: GeographicArea }) {
  const dominantState = dominantWorkflowState(area.workflowStates)
  const query = new URLSearchParams({ district: area.district }).toString()
  return (
    <div className="flex flex-1 flex-col px-4 py-4">
      <p className="font-mono text-xs text-ardosia">{area.municipality}</p>
      <h3 className="mt-1 text-lg font-semibold text-encontro">{area.district}</h3>
      <p className="mt-1 text-sm text-grafite">{area.signals} sinal{area.signals === 1 ? '' : 'is'} consolidado{area.signals === 1 ? '' : 's'}</p>

      <dl className="mt-4 grid grid-cols-2 gap-3 border-y border-agua py-3">
        <div>
          <dt className="flex items-center gap-1 text-xs text-ardosia"><Newspaper className="size-3.5" aria-hidden /> Mídia</dt>
          <dd className="mt-0.5 text-lg font-semibold text-grafite">{area.sourceCounts.media}</dd>
        </div>
        <div>
          <dt className="flex items-center gap-1 text-xs text-ardosia"><MessagesSquare className="size-3.5" aria-hidden /> Comunidade</dt>
          <dd className="mt-0.5 text-lg font-semibold text-grafite">{area.sourceCounts.community}</dd>
        </div>
      </dl>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
        <div>
          <p className="text-xs font-medium text-ardosia">Condição mais frequente</p>
          <p className="mt-1 text-sm text-grafite">{area.topCondition?.label ?? 'Não informada'}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-ardosia">Estado predominante</p>
          <div className="mt-1"><StateLabel state={dominantState} /></div>
        </div>
      </div>

      <Button
        variant="outline"
        size="sm"
        className="mt-5 w-full"
        render={<Link href={`/triagem?${query}`} />}
        nativeButton={false}
      >
        Ver sinais desta área <ArrowRight aria-hidden />
      </Button>
    </div>
  )
}

function dominantWorkflowState(states: Record<string, number>): WorkflowState {
  const [state] = Object.entries(states).sort(([leftKey, leftCount], [rightKey, rightCount]) =>
    rightCount - leftCount || leftKey.localeCompare(rightKey),
  )[0] ?? ['detected', 0]
  return API_TO_UI_STATE[state] ?? 'detectado'
}

function EmptyPanorama() {
  return (
    <div className="mx-auto flex w-full max-w-[880px] flex-col gap-5 px-4 py-8 md:px-6 md:py-12">
      <PageHeader
        title="Panorama territorial"
        description="Distribuição agregada dos sinais sintéticos consolidados."
        meta="Dataset sintético · nenhuma janela disponível"
      />
      <section className="rounded-md border border-dashed border-agua-strong bg-mineral px-5 py-10 text-center">
        <MapPinned className="mx-auto size-7 text-igarape" aria-hidden />
        <h2 className="mt-3 text-lg font-semibold text-encontro">Nenhum sinal consolidado para o panorama</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-ardosia">
          Carregue o cenário sintético canônico com <code className="rounded-sm bg-nevoa px-1 py-0.5 font-mono text-xs text-grafite">docker compose --profile tools run --rm demo-load</code> e atualize esta página.
        </p>
      </section>
    </div>
  )
}
