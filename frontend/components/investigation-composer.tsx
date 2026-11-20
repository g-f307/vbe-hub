'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { signalHref } from '@/lib/signal-navigation'
import { AlertTriangle, CheckCircle2, Clock3, LoaderCircle } from 'lucide-react'

import {
  composeInvestigation,
  createInvestigationOperationKey,
  hideInvestigationMembers,
  type InvestigationDetail,
  removeInvestigationMember,
  selectableRelatedSignals,
} from '@/lib/investigation-client'
import type {
  IndividualSignalDetail,
  RelatedSignal,
  RelatedSignalPage,
} from '@/lib/individual-signal-read'
import { Button } from '@/components/ui/button'
import { EvidenceTimeline } from '@/components/evidence-timeline'

export function InvestigationComposer({
  signal,
  related,
  returnTo,
  initialInvestigation,
  mode = 'related',
  onChange,
  onBusy,
}: {
  signal: IndividualSignalDetail
  related: RelatedSignalPage
  returnTo: string
  initialInvestigation: InvestigationDetail | null
  mode?: 'related' | 'evidence'
  onChange: (value: InvestigationDetail) => void
  onBusy?: (busy: boolean) => void
}) {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [expandedSuggestionIds, setExpandedSuggestionIds] = useState<string[]>(
    [],
  )
  const [visibleRelated, setVisibleRelated] = useState(() => related.items)
  const investigation = initialInvestigation
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [removeTarget, setRemoveTarget] = useState<string | null>(null)
  const [removeReason, setRemoveReason] = useState('analyst-correction')
  const selectable = useMemo(
    () =>
      selectableRelatedSignals(visibleRelated).filter(
        (item) =>
          item.candidate.id !== signal.id &&
          !investigation?.members.some(
            (member) => member.signal.id === item.candidate.id,
          ),
      ),
    [investigation, visibleRelated, signal.id],
  )
  const selected = selectable.filter((item) =>
    selectedIds.includes(item.candidate.id),
  )

  function toggle(signalId: string) {
    setSelectedIds((current) =>
      current.includes(signalId)
        ? current.filter((id) => id !== signalId)
        : [...current, signalId],
    )
  }

  async function confirmComposition() {
    setPending(true)
    onBusy?.(true)
    setError(null)
    try {
      const result = await composeInvestigation({
        primarySignalId: signal.id,
        selectedSignalIds: selectedIds,
        operationKey: createInvestigationOperationKey('compose'),
      })
      onChange(result)
      setVisibleRelated((current) =>
        hideInvestigationMembers(
          current,
          result.members.map((member) => member.signal.id),
        ),
      )
      setSelectedIds([])
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'Não foi possível registrar a decisão.',
      )
    } finally {
      setPending(false)
      onBusy?.(false)
    }
  }

  async function confirmRemoval() {
    if (!investigation || !removeTarget) return
    setPending(true)
    onBusy?.(true)
    setError(null)
    try {
      const result = await removeInvestigationMember({
        investigationId: investigation.id,
        signalId: removeTarget,
        expectedVersion: investigation.version,
        operationKey: createInvestigationOperationKey('remove'),
        reasonCode: removeReason,
      })
      onChange(result)
      setRemoveTarget(null)
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'Não foi possível corrigir a composição.',
      )
    } finally {
      setPending(false)
      onBusy?.(false)
    }
  }

  return (
    <div className="space-y-7">
      {mode === 'evidence' ? (
        investigation ? (
          <InvestigationSummary
            investigation={investigation}
            returnTo={returnTo}
            onRemove={setRemoveTarget}
          />
        ) : (
          <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            Ainda não há evidências incorporadas a este sinal.
          </p>
        )
      ) : null}

      {mode === 'related' ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {visibleRelated
            .filter(
              (item) =>
                item.candidate.id !== signal.id &&
                !investigation?.members.some(
                  (member) => member.signal.id === item.candidate.id,
                ) &&
                (item.status !== 'ready' ||
                  selectable.some(
                    (candidate) => candidate.suggestionId === item.suggestionId,
                  )),
            )
            .map((item) => {
              const canSelect = selectable.some(
                (candidate) => candidate.suggestionId === item.suggestionId,
              )
              const checked = selectedIds.includes(item.candidate.id)
              const expanded = expandedSuggestionIds.includes(item.suggestionId)
              const canExpand = (item.justification?.length ?? 0) > 120
              return (
                <article
                  key={item.suggestionId}
                  data-candidate-card="kanban"
                  data-workflow-state={item.candidate.state}
                  className={`workflow-candidate relative rounded-xl border border-t-4 bg-background p-4 ${checked ? 'ring-2 ring-primary/20' : 'border-x-border border-b-border'}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-xs text-muted-foreground">
                      {item.candidate.sourceKind === 'media'
                        ? 'Mídia'
                        : 'Relato comunitário'}
                    </span>
                    <SuggestionState item={item} />
                  </div>
                  <h3 className="mt-2 text-sm font-semibold leading-snug">
                    {item.candidate.title}
                  </h3>
                  <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                    {item.candidate.excerpt}
                  </p>
                  {item.status === 'ready' ? (
                    <div className="mt-3 border-t border-border pt-3 text-xs">
                      <p className="font-medium text-primary">
                        Possível relação
                      </p>
                      <p
                        className={`mt-1 leading-relaxed text-muted-foreground ${expanded ? '' : 'line-clamp-2'}`}
                      >
                        {item.justification ?? 'Justificativa não informada.'}
                      </p>
                      {canExpand ? (
                        <button
                          type="button"
                          aria-expanded={expanded}
                          onClick={() =>
                            setExpandedSuggestionIds((current) =>
                              current.includes(item.suggestionId)
                                ? current.filter(
                                    (id) => id !== item.suggestionId,
                                  )
                                : [...current, item.suggestionId],
                            )
                          }
                          className="mt-1.5 font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          {expanded ? 'Ler menos' : 'Ler mais'}
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                  <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3">
                    {canSelect ? (
                      <label className="flex min-h-9 cursor-pointer items-center gap-2 text-xs font-medium">
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={pending}
                          onChange={() => toggle(item.candidate.id)}
                          className="peer size-4 accent-[var(--primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                        />
                        Selecionar sinal
                      </label>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        {item.candidate.activeInvestigationId
                          ? 'Já pertence a outra ficha'
                          : 'Disponível somente após o processamento'}
                      </span>
                    )}
                    <Link
                      href={relatedHref(signal.id, item.candidate.id, returnTo)}
                      className="inline-flex min-h-9 items-center text-xs font-medium text-primary hover:underline"
                    >
                      Consultar
                    </Link>
                  </div>
                </article>
              )
            })}
        </div>
      ) : null}

      {mode === 'related' && selectable.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">
          Nenhum novo sinal disponível para seleção.
        </p>
      ) : null}

      {mode === 'related' && selected.length > 0 ? (
        <div
          className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-5"
          aria-live="polite"
        >
          <div className="mr-auto min-w-0 text-sm">
            <p className="font-medium">Sinal principal: {signal.title}</p>
            <p className="text-xs text-muted-foreground">
              Serão incorporados:{' '}
              {selected.map((item) => item.candidate.title).join('; ')}
            </p>
          </div>
          <p className="text-sm text-muted-foreground">
            {selected.length} selecionado(s)
          </p>
          <Button
            type="button"
            size="lg"
            onClick={confirmComposition}
            disabled={pending}
          >
            {pending ? (
              <LoaderCircle className="animate-spin" aria-hidden />
            ) : (
              <CheckCircle2 aria-hidden />
            )}
            {pending ? 'Adicionando…' : 'Adicionar selecionados à ficha'}
          </Button>
        </div>
      ) : null}

      {removeTarget && investigation ? (
        <section
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirmar-remocao"
          className="rounded-xl border border-destructive/30 bg-card p-5"
        >
          <h3 id="confirmar-remocao" className="font-semibold">
            Corrigir associação
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            A remoção não apaga o sinal e ficará registrada na trilha da ficha.
          </p>
          <label
            className="mt-4 block text-sm font-medium"
            htmlFor="remove-reason"
          >
            Motivo obrigatório
          </label>
          <select
            id="remove-reason"
            value={removeReason}
            onChange={(event) => setRemoveReason(event.target.value)}
            className="mt-1 min-h-11 w-full rounded-md border border-input bg-background px-3 text-sm sm:max-w-md"
          >
            <option value="analyst-correction">Correção do analista</option>
            <option value="insufficient-relation">Relação insuficiente</option>
            <option value="different-event">Evento diferente</option>
          </select>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setRemoveTarget(null)}
              disabled={pending}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={confirmRemoval}
              disabled={pending}
            >
              Confirmar correção
            </Button>
          </div>
        </section>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
        >
          <AlertTriangle className="mr-2 inline size-4" aria-hidden />
          {error}
        </p>
      ) : null}
    </div>
  )
}

function InvestigationSummary({
  investigation,
  onRemove,
  returnTo,
}: {
  investigation: InvestigationDetail
  onRemove: (signalId: string) => void
  returnTo: string
}) {
  const evidence = investigation.members.filter(
    (member) => member.signal.id !== investigation.headSignalId,
  )
  if (evidence.length === 0)
    return (
      <p className="rounded-lg border border-dashed border-border p-5 text-center text-sm text-muted-foreground">
        Nenhuma evidência foi incorporada.
      </p>
    )
  return (
    <EvidenceTimeline
      items={evidence}
      headSignalId={investigation.headSignalId}
      returnTo={returnTo}
      originTab="evidence"
      layout="grid"
      onRemove={onRemove}
    />
  )
}

function SuggestionState({ item }: { item: RelatedSignal }) {
  if (item.status === 'pending')
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
        <Clock3 className="size-3.5" aria-hidden /> Processamento em andamento
      </span>
    )
  if (item.status === 'failed')
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-destructive">
        <AlertTriangle className="size-3.5" aria-hidden /> Não foi possível
        preparar esta sugestão
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-andiroba">
      <CheckCircle2 className="size-3.5" aria-hidden /> Sugestão disponível
    </span>
  )
}

function relatedHref(
  originId: string,
  candidateId: string,
  returnTo: string,
): string {
  const relatedReturn = `${signalHref(originId, 'evidence', returnTo)}&candidates=open`
  return `/sinais/${candidateId}?${new URLSearchParams({ returnTo: relatedReturn })}`
}

export function normalizeInvestigation(
  value: import('@/lib/individual-signal-read').InvestigationDetail | null,
): InvestigationDetail | null {
  if (!value) return null
  return {
    id: value.id,
    headSignalId: value.headSignalId,
    version: value.version,
    createdAt: value.createdAt,
    updatedAt: value.updatedAt,
    technicalSheet: value.technicalSheet,
    information: value.information,
    technicalSheetProvenance: value.technicalSheetProvenance,
    technicalSheetConflicts: value.technicalSheetConflicts,
    members: value.members.map((member) => ({
      addedAt: member.addedAt,
      addedBy: member.addedBy,
      signal: {
        id: member.signal.id,
        title: member.signal.title,
        body: member.signal.source.body,
        sourceKind: member.signal.sourceKind,
        sourceName: member.signal.sourceName,
        publishedAt: member.signal.publishedAt,
      },
    })),
    events: value.events,
  }
}
