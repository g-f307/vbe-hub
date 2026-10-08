'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { ArrowRight, ChartNoAxesCombined, MapPinned, MessagesSquare, Newspaper, ScanSearch } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { StateLabel } from '@/components/status-badges'
import { Button } from '@/components/ui/button'
import { DAILY_SERIES, NEIGHBORHOODS, PANORAMA_TOTALS, PIPELINE_FUNNEL, PIPELINE_QUALITY, TOP_CONDITIONS } from '@/lib/mock-data'
import { cn } from '@/lib/utils'

const METRICS = [
  { key: 'signals', label: 'Sinais no período', detail: 'Registros consolidados para leitura da vigilância' },
  { key: 'awaitingTriage', label: 'Aguardando triagem', detail: 'Necessitam decisão humana na fila' },
  { key: 'multiSource', label: 'Com mais de uma fonte', detail: 'Mídia e comunidade ou fontes independentes' },
  { key: 'divergent', label: 'Com divergência', detail: 'Exigem conferência explícita das evidências' },
] as const

export function PanoramaBoard() {
  const [selectedId, setSelectedId] = useState(NEIGHBORHOODS[0].id)
  const selected = useMemo(() => NEIGHBORHOODS.find((neighborhood) => neighborhood.id === selectedId) ?? NEIGHBORHOODS[0], [selectedId])
  const maxSeries = Math.max(...DAILY_SERIES.map((point) => point.sinais))
  const maxCondition = Math.max(...TOP_CONDITIONS.map((condition) => condition.count))

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 md:px-6 md:py-6 lg:px-8">
      <PageHeader
        title="Panorama dos sinais"
        description="Leitura territorial e operacional dos registros sintéticos já consolidados. Não representa confirmação de eventos de saúde."
        meta={`Manaus, AM · Período ${PANORAMA_TOTALS.periodLabel}`}
        actions={<Button variant="outline" render={<Link href="/triagem" />} nativeButton={false}>Abrir fila <ArrowRight aria-hidden /></Button>}
      />

      <section aria-label="Resumo do período" className="grid gap-px overflow-hidden rounded-md border border-agua bg-agua sm:grid-cols-2 xl:grid-cols-4">
        {METRICS.map((metric) => (
          <div key={metric.key} className="bg-mineral px-4 py-4">
            <p className="text-sm text-ardosia">{metric.label}</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-encontro">{PANORAMA_TOTALS[metric.key]}</p>
            <p className="mt-1 text-xs leading-relaxed text-ardosia">{metric.detail}</p>
          </div>
        ))}
      </section>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,0.75fr)]">
        <section aria-labelledby="territorio-titulo" className="overflow-hidden rounded-md border border-agua bg-mineral">
          <div className="flex flex-col gap-1 border-b border-agua px-4 py-3 md:flex-row md:items-center md:justify-between md:px-5">
            <div>
              <h2 id="territorio-titulo" className="text-base font-semibold text-encontro">Distribuição por território</h2>
              <p className="mt-0.5 text-sm text-ardosia">Selecione um bairro para conhecer a composição dos sinais.</p>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs text-ardosia"><MapPinned className="size-4 text-igarape" aria-hidden /> Diagrama territorial ilustrativo</span>
          </div>
          <div className="grid lg:grid-cols-[minmax(0,1fr)_240px]">
            <div className="relative min-h-80 overflow-hidden bg-nevoa p-4" aria-label="Diagrama de bairros de Manaus">
              <svg viewBox="0 0 960 560" className="absolute inset-0 size-full text-agua-strong" aria-hidden>
                <path d="M-10 330 C120 270 194 356 306 306 S495 210 615 274 S780 374 970 276" fill="none" stroke="currentColor" strokeWidth="18" strokeLinecap="round" opacity="0.7" />
                <path d="M15 138 C180 174 281 89 429 141 S695 153 953 72" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="8 10" />
                <path d="M40 478 C193 389 388 474 516 407 S759 409 920 500" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="8 10" />
              </svg>
              {NEIGHBORHOODS.map((neighborhood) => {
                const active = neighborhood.id === selected.id
                return (
                  <button
                    key={neighborhood.id}
                    type="button"
                    onClick={() => setSelectedId(neighborhood.id)}
                    aria-pressed={active}
                    className={cn('absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-nevoa transition-transform focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-igarape', active ? 'scale-110 bg-urucum text-mineral' : 'bg-igarape text-mineral hover:scale-105')}
                    style={{ left: `${(neighborhood.x / 960) * 100}%`, top: `${(neighborhood.y / 560) * 100}%`, width: `${34 + neighborhood.signals * 4}px`, height: `${34 + neighborhood.signals * 4}px` }}
                  >
                    <span className="sr-only">{neighborhood.name}: {neighborhood.signals} sinais</span>
                    <span className="text-sm font-semibold" aria-hidden>{neighborhood.signals}</span>
                  </button>
                )
              })}
              <p className="absolute bottom-3 left-4 rounded-sm bg-mineral/90 px-2 py-1 text-xs text-ardosia">O tamanho do marcador indica o total de sinais no período.</p>
            </div>
            <div className="border-t border-agua p-4 lg:border-t-0 lg:border-l">
              <p className="font-mono text-xs text-ardosia">{selected.name}</p>
              <h3 className="mt-1 text-lg font-semibold text-encontro">{selected.signals} sinais registrados</h3>
              <dl className="mt-4 grid grid-cols-2 gap-3 border-y border-agua py-3">
                <div><dt className="flex items-center gap-1 text-xs text-ardosia"><Newspaper className="size-3.5" /> Mídia</dt><dd className="mt-0.5 text-lg font-semibold text-grafite">{selected.media}</dd></div>
                <div><dt className="flex items-center gap-1 text-xs text-ardosia"><MessagesSquare className="size-3.5" /> Comunidade</dt><dd className="mt-0.5 text-lg font-semibold text-grafite">{selected.community}</dd></div>
              </dl>
              <div className="mt-4"><p className="text-xs font-medium text-ardosia">Condições mais mencionadas</p><ul className="mt-2 flex flex-col gap-2">{selected.conditions.map((condition) => <li key={condition.label} className="flex justify-between gap-2 text-sm text-grafite"><span>{condition.label}</span><span className="font-mono text-ardosia">{condition.count}</span></li>)}</ul></div>
              <div className="mt-4"><p className="text-xs font-medium text-ardosia">Estado predominante</p><div className="mt-2"><StateLabel state={selected.dominantState} /></div></div>
              <Button variant="outline" size="sm" className="mt-4 w-full" render={<Link href={`/triagem?bairro=${encodeURIComponent(selected.name)}`} />} nativeButton={false}>Ver sinais na fila <ArrowRight aria-hidden /></Button>
            </div>
          </div>
        </section>

        <section aria-labelledby="condicoes-titulo" className="rounded-md border border-agua bg-mineral px-4 py-4 md:px-5">
          <h2 id="condicoes-titulo" className="text-base font-semibold text-encontro">Condições mais mencionadas</h2>
          <p className="mt-1 text-sm text-ardosia">Rótulos extraídos; não equivalem a diagnósticos.</p>
          <ol className="mt-4 flex flex-col gap-3">
            {TOP_CONDITIONS.map((condition, index) => (
              <li key={condition.label} className="grid grid-cols-[1.5rem_minmax(0,1fr)_2rem] items-center gap-2">
                <span className="font-mono text-xs text-ardosia">{String(index + 1).padStart(2, '0')}</span>
                <span className="min-w-0"><span className="block text-sm text-grafite">{condition.label}</span><span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-agua"><span className="block h-full rounded-full bg-igarape" style={{ width: `${(condition.count / maxCondition) * 100}%` }} /></span></span>
                <span className="text-right text-sm font-semibold text-encontro">{condition.count}</span>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <section aria-labelledby="serie-titulo" className="rounded-md border border-agua bg-mineral px-4 py-4 md:px-5">
          <div className="flex items-start justify-between gap-4"><div><h2 id="serie-titulo" className="text-base font-semibold text-encontro">Ritmo de entrada</h2><p className="mt-1 text-sm text-ardosia">Registros recebidos e sinais consolidados por dia.</p></div><ChartNoAxesCombined className="size-5 text-igarape" aria-hidden /></div>
          <div className="mt-5 flex h-36 items-end gap-1" aria-label="Gráfico de barras de sinais consolidados por dia">
            {DAILY_SERIES.map((point) => <div key={point.date} className="group relative flex h-full min-w-0 flex-1 items-end"><span className="w-full rounded-t-sm bg-igarape/85 group-hover:bg-igarape" style={{ height: `${Math.max(8, (point.sinais / maxSeries) * 100)}%` }} title={`${point.label}: ${point.sinais} sinais`} /><span className="sr-only">{point.label}: {point.sinais} sinais</span></div>)}
          </div>
          <div className="mt-2 flex justify-between text-xs text-ardosia"><span>{DAILY_SERIES[0].label}</span><span>{DAILY_SERIES.at(-1)?.label}</span></div>
        </section>

        <section aria-labelledby="fluxo-titulo" className="rounded-md border border-agua bg-mineral px-4 py-4 md:px-5">
          <h2 id="fluxo-titulo" className="text-base font-semibold text-encontro">Fluxo de processamento</h2>
          <p className="mt-1 text-sm text-ardosia">Visão operacional do lote mais recente.</p>
          <ol className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-agua bg-agua sm:grid-cols-4">
            {PIPELINE_FUNNEL.map((step) => <li key={step.label} className="bg-mineral p-3"><p className="text-2xl font-semibold text-encontro">{step.value}</p><p className="mt-1 text-xs leading-relaxed text-ardosia">{step.label}</p></li>)}
          </ol>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {PIPELINE_QUALITY.map((metric) => <div key={metric.key} className="rounded-sm border border-agua px-3 py-2.5"><p className="text-xs text-ardosia">{metric.label}</p><p className={cn('mt-0.5 text-lg font-semibold', metric.tone === 'erro' ? 'text-urucum-ink' : 'text-encontro')}>{metric.value}</p><p className="mt-0.5 text-xs text-ardosia">{metric.description}</p></div>)}
          </div>
          <p className="mt-4 flex gap-2 rounded-sm border border-dashed border-agua-strong px-3 py-2 text-xs leading-relaxed text-ardosia"><ScanSearch className="mt-0.5 size-4 shrink-0 text-igarape" aria-hidden />Estas métricas descrevem o processamento técnico de dados sintéticos; não medem ocorrência de doença.</p>
        </section>
      </div>
    </div>
  )
}
