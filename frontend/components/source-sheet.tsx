'use client'

import { useState } from 'react'
import { ChevronDown, ExternalLink } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { SourceTypeIcon } from '@/components/status-badges'
import { formatDateTime } from '@/lib/format'
import { SOURCE_TYPE_LABEL } from '@/lib/labels'
import type { SourceRecord } from '@/lib/types'
import { cn } from '@/lib/utils'

export type SourceTab = 'todas' | 'midia' | 'comunidade'

export function SourceSheets({
  sources,
  removedIds,
  tab,
  onTabChange,
  expandedIds,
  onExpandedChange,
}: {
  sources: SourceRecord[]
  removedIds: string[]
  tab: SourceTab
  onTabChange: (tab: SourceTab) => void
  expandedIds: string[]
  onExpandedChange: (id: string, open: boolean) => void
}) {
  const [originSource, setOriginSource] = useState<SourceRecord | null>(null)
  const counts = {
    todas: sources.length,
    midia: sources.filter((s) => s.type === 'midia').length,
    comunidade: sources.filter((s) => s.type === 'comunidade').length,
  }

  return (
    <section aria-labelledby="fichas-titulo" className="rounded-md border border-agua bg-mineral px-4 py-4 md:px-5">
      <h2 id="fichas-titulo" className="text-base font-semibold text-encontro">
        Fontes e fichas técnicas
      </h2>
      <p className="mt-1 text-sm text-ardosia">Campos extraídos automaticamente de cada registro. Confira antes de decidir.</p>

      <Tabs value={tab} onValueChange={(value) => onTabChange(value as SourceTab)} className="mt-3">
        <TabsList className="h-9">
          <TabsTrigger value="todas" className="px-3">
            Todas ({counts.todas})
          </TabsTrigger>
          <TabsTrigger value="midia" className="px-3">
            Mídia ({counts.midia})
          </TabsTrigger>
          <TabsTrigger value="comunidade" className="px-3">
            Comunidade ({counts.comunidade})
          </TabsTrigger>
        </TabsList>

        {(['todas', 'midia', 'comunidade'] as const).map((value) => (
          <TabsContent key={value} value={value} className="mt-3">
            <ul className="flex flex-col gap-2">
              {sources
                .filter((s) => value === 'todas' || s.type === value)
                .map((source) => (
                  <SourceCard
                    key={source.id}
                    source={source}
                    removed={removedIds.includes(source.id)}
                    open={expandedIds.includes(source.id)}
                    onOpenChange={(open) => onExpandedChange(source.id, open)}
                    onOpenOrigin={() => setOriginSource(source)}
                  />
                ))}
            </ul>
          </TabsContent>
        ))}
      </Tabs>

      <OriginRecordDialog source={originSource} onClose={() => setOriginSource(null)} />
    </section>
  )
}

function SourceCard({
  source,
  removed,
  open,
  onOpenChange,
  onOpenOrigin,
}: {
  source: SourceRecord
  removed: boolean
  open: boolean
  onOpenChange: (open: boolean) => void
  onOpenOrigin: () => void
}) {
  const { sheet } = source
  return (
    <li id={`ficha-${source.id}`} className="scroll-mt-20">
      <Collapsible
        open={open}
        onOpenChange={onOpenChange}
        className={cn('rounded-md border', open ? 'border-igarape/40' : 'border-agua', removed && 'bg-muted/60')}
      >
        <CollapsibleTrigger className="flex min-h-12 w-full items-center gap-3 rounded-md px-3 py-2.5 text-left hover:bg-nevoa">
          <SourceTypeIcon type={source.type} className={source.type === 'midia' ? 'text-encontro' : 'text-igarape'} />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-encontro">{source.title}</span>
            <span className="block text-xs text-ardosia">
              <span className="font-mono">{source.code}</span> · {SOURCE_TYPE_LABEL[source.type]} · {source.subtype}
              {removed && ' · removido do sinal'}
            </span>
          </span>
          <ChevronDown className={cn('size-4 shrink-0 text-ardosia transition-transform', open && 'rotate-180')} aria-hidden />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t border-agua px-3 py-3">
            {sheet ? <>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
              <Field term="Condição">{sheet.condition}</Field>
              <Field term="Sintomas">{sheet.symptoms.length ? sheet.symptoms.join(', ') : null}</Field>
              <Field term="Local">{sheet.location}</Field>
              <Field term="Período">{sheet.period}</Field>
              <Field term="Magnitude">{sheet.magnitude}</Field>
              <Field term="Campos ausentes">
                {sheet.missingFields.length ? (
                  <ul className="flex flex-wrap gap-1">
                    {sheet.missingFields.map((f) => (
                      <li key={f} className="rounded-sm border border-dashed border-agua-strong px-1.5 py-px text-xs text-ardosia">
                        {f}
                      </li>
                    ))}
                  </ul>
                ) : (
                  'Nenhum'
                )}
              </Field>
              <Field term="Versão da extração">
                <span className="font-mono text-xs">{sheet.extractionVersion}</span>
              </Field>
              <Field term="Data de extração">{sheet.extractedAt ? formatDateTime(sheet.extractedAt) : null}</Field>
            </dl>
            </> : <p className="rounded-sm border border-dashed border-agua-strong bg-nevoa px-3 py-2.5 text-sm text-ardosia">Nenhuma ficha técnica bem-sucedida está disponível para este registro.</p>}
            <div className="mt-3 flex justify-end border-t border-agua pt-3">
              <Button variant="outline" size="sm" onClick={onOpenOrigin}>
                <ExternalLink aria-hidden />
                Abrir registro de origem
              </Button>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </li>
  )
}

function Field({ term, children }: { term: string; children: React.ReactNode }) {
  const empty = children === null || children === undefined || children === ''
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium text-ardosia">{term}</dt>
      <dd className={cn('mt-0.5 text-sm', empty ? 'text-ardosia italic' : 'text-grafite')}>
        {empty ? 'Não identificado' : children}
      </dd>
    </div>
  )
}

function OriginRecordDialog({ source, onClose }: { source: SourceRecord | null; onClose: () => void }) {
  return (
    <Dialog open={source !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        {source && (
          <>
            <DialogHeader>
              <p className="font-mono text-xs text-ardosia">{source.code}</p>
              <DialogTitle className="text-pretty">{source.title}</DialogTitle>
              <DialogDescription>
                {source.origin} · {formatDateTime(source.publishedAt)}
              </DialogDescription>
            </DialogHeader>
            <blockquote className="rounded-sm border-l-2 border-igarape bg-nevoa px-3 py-2.5 text-sm text-pretty text-grafite">
              {source.excerpt}
            </blockquote>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-ardosia">Tipo</dt>
                <dd className="text-grafite">
                  {SOURCE_TYPE_LABEL[source.type]} · {source.subtype}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-ardosia">Local declarado</dt>
                <dd className="text-grafite">
                  {source.municipality}, {source.neighborhood}
                </dd>
              </div>
            </dl>
            <p className="rounded-sm border border-dashed border-agua-strong px-3 py-2 text-xs text-pretty text-ardosia">
              Registro sintético para demonstração. O painel preserva o vínculo com a evidência armazenada pelo pipeline e não exibe dados pessoais.
            </p>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Fechar</DialogClose>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
