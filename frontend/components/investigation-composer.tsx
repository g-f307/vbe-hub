'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock3, FileCheck2, LoaderCircle, Users } from 'lucide-react'

import {
  composeInvestigation,
  createInvestigationOperationKey,
  type InvestigationDetail,
  removeInvestigationMember,
  selectableRelatedSignals,
} from '@/lib/investigation-client'
import type {
  IndividualSignalDetail,
  InvestigationDetail as ReadInvestigationDetail,
  RelatedSignal,
  RelatedSignalPage,
} from '@/lib/individual-signal-read'
import { Badge } from '@/v0/components/ui/badge'
import { Button } from '@/components/ui/button'

export function InvestigationComposer({
  signal,
  related,
  returnTo,
  initialInvestigation,
}: {
  signal: IndividualSignalDetail
  related: RelatedSignalPage
  returnTo: string
  initialInvestigation: ReadInvestigationDetail | null
}) {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [reviewing, setReviewing] = useState(false)
  const [investigation, setInvestigation] = useState<InvestigationDetail | null>(() => normalizeInvestigation(initialInvestigation))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [removeTarget, setRemoveTarget] = useState<string | null>(null)
  const [removeReason, setRemoveReason] = useState('analyst-correction')
  const selectable = useMemo(
    () => selectableRelatedSignals(related.items).filter((item) => !investigation?.members.some((member) => member.signal.id === item.candidate.id)),
    [investigation, related.items],
  )
  const selected = selectable.filter((item) => selectedIds.includes(item.candidate.id))

  function toggle(signalId: string) {
    setSelectedIds((current) => current.includes(signalId) ? current.filter((id) => id !== signalId) : [...current, signalId])
  }

  async function confirmComposition() {
    setPending(true)
    setError(null)
    try {
      const result = await composeInvestigation({
        primarySignalId: signal.id,
        selectedSignalIds: selectedIds,
        operationKey: createInvestigationOperationKey('compose'),
      })
      setInvestigation(result)
      setSelectedIds([])
      setReviewing(false)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível registrar a decisão.')
    } finally {
      setPending(false)
    }
  }

  async function confirmRemoval() {
    if (!investigation || !removeTarget) return
    setPending(true)
    setError(null)
    try {
      const result = await removeInvestigationMember({
        investigationId: investigation.id,
        signalId: removeTarget,
        expectedVersion: investigation.version,
        operationKey: createInvestigationOperationKey('remove'),
        reasonCode: removeReason,
      })
      setInvestigation(result)
      setRemoveTarget(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Não foi possível corrigir a composição.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="space-y-7">
      {investigation ? <InvestigationSummary investigation={investigation} onRemove={setRemoveTarget} /> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {related.items.map((item) => {
          const canSelect = selectable.some((candidate) => candidate.suggestionId === item.suggestionId)
          const checked = selectedIds.includes(item.candidate.id)
          return (
            <article key={item.suggestionId} className={`rounded-xl border bg-background p-5 ${checked ? 'border-primary ring-2 ring-primary/15' : 'border-border'}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge variant="outline">{item.candidate.sourceKind === 'media' ? 'Mídia' : 'Relato comunitário'}</Badge>
                <SuggestionState item={item} />
              </div>
              <h3 className="mt-3 text-base font-semibold leading-snug">{item.candidate.title}</h3>
              <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted-foreground">{item.candidate.excerpt}</p>
              {item.status === 'ready' ? (
                <div className="mt-4 rounded-lg bg-muted/50 p-3 text-sm">
                  <p className="font-medium">{relationLabel(item.relation)}{item.confidence === null ? '' : ` · ${Math.round(item.confidence * 100)}% de confiança técnica`}</p>
                  <p className="mt-1 leading-relaxed text-muted-foreground">{item.justification ?? 'Justificativa não informada.'}</p>
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
                {canSelect ? (
                  <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-medium">
                    <input type="checkbox" checked={checked} onChange={() => toggle(item.candidate.id)} className="size-4 accent-primary" />
                    Selecionar {item.candidate.title}
                  </label>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    {item.candidate.activeInvestigationId ? 'Já pertence a outra ficha' : 'Disponível somente após o processamento'}
                  </span>
                )}
                <Link href={relatedHref(signal.id, item.candidate.id, returnTo)} className="inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline">
                  Abrir este sinal
                </Link>
              </div>
            </article>
          )
        })}
      </div>

      <section aria-labelledby="decisao-composicao" className="rounded-xl border border-andiroba/30 bg-andiroba/5 p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 id="decisao-composicao" className="font-semibold">Decisão de composição</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {selected.length > 0 ? `${selected.length} sinal(is) relacionado(s) selecionado(s).` : 'Criar ficha apenas com o sinal principal.'}
              {' '}A associação só será registrada após sua confirmação.
            </p>
          </div>
          <Button type="button" size="lg" onClick={() => setReviewing(true)} disabled={pending}>
            <FileCheck2 aria-hidden /> Revisar composição
          </Button>
        </div>
      </section>

      {reviewing ? (
        <section role="dialog" aria-modal="true" aria-labelledby="confirmar-composicao" className="rounded-xl border-2 border-primary/30 bg-card p-5 shadow-lg">
          <h3 id="confirmar-composicao" className="text-lg font-semibold">Confirmar composição da ficha</h3>
          <p className="mt-1 text-sm text-muted-foreground">Confira exatamente quais sinais serão reunidos. Os textos continuarão separados.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <ComparisonCard id={signal.id} title={signal.title} body={signal.source.body} label="Sinal principal" />
            {selected.map((item) => <ComparisonCard key={item.candidate.id} id={item.candidate.id} title={item.candidate.title} body={item.candidate.excerpt} label="Sinal relacionado" />)}
          </div>
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setReviewing(false)} disabled={pending}>Cancelar</Button>
            <Button type="button" onClick={confirmComposition} disabled={pending}>
              {pending ? <LoaderCircle className="animate-spin" aria-hidden /> : <CheckCircle2 aria-hidden />}
              Confirmar composição
            </Button>
          </div>
        </section>
      ) : null}

      {removeTarget && investigation ? (
        <section role="dialog" aria-modal="true" aria-labelledby="confirmar-remocao" className="rounded-xl border border-destructive/30 bg-card p-5">
          <h3 id="confirmar-remocao" className="font-semibold">Corrigir associação</h3>
          <p className="mt-1 text-sm text-muted-foreground">A remoção não apaga o sinal e ficará registrada na trilha da ficha.</p>
          <label className="mt-4 block text-sm font-medium" htmlFor="remove-reason">Motivo obrigatório</label>
          <select id="remove-reason" value={removeReason} onChange={(event) => setRemoveReason(event.target.value)} className="mt-1 min-h-11 w-full rounded-md border border-input bg-background px-3 text-sm sm:max-w-md">
            <option value="analyst-correction">Correção do analista</option>
            <option value="insufficient-relation">Relação insuficiente</option>
            <option value="different-event">Evento diferente</option>
          </select>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setRemoveTarget(null)} disabled={pending}>Cancelar</Button>
            <Button type="button" variant="destructive" onClick={confirmRemoval} disabled={pending}>Confirmar correção</Button>
          </div>
        </section>
      ) : null}

      {error ? <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"><AlertTriangle className="mr-2 inline size-4" aria-hidden />{error}</p> : null}
    </div>
  )
}

function InvestigationSummary({ investigation, onRemove }: { investigation: InvestigationDetail; onRemove: (signalId: string) => void }) {
  return (
    <section aria-labelledby="ficha-ativa" className="rounded-xl border border-primary/25 bg-primary/5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h3 id="ficha-ativa" className="flex items-center gap-2 font-semibold"><Users className="size-4" aria-hidden /> Ficha de investigação ativa</h3><p className="mt-1 font-mono text-xs text-muted-foreground">{investigation.id} · versão {investigation.version}</p></div>
        <Badge>{investigation.members.length} fonte(s)</Badge>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {investigation.members.map((member) => (
          <article key={member.signal.id} className="rounded-lg border border-border bg-background p-4">
            <p className="text-xs text-muted-foreground">{member.signal.sourceName} · {member.signal.sourceKind === 'media' ? 'Mídia' : 'Comunidade'}</p>
            <h4 className="mt-1 font-medium">{member.signal.title}</h4>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{member.signal.body}</p>
            <p className="mt-3 font-mono text-[11px] text-muted-foreground">{member.signal.id}</p>
            {investigation.members.length > 1 ? <Button type="button" variant="destructive" size="sm" className="mt-3" onClick={() => onRemove(member.signal.id)}>Remover da ficha</Button> : null}
          </article>
        ))}
      </div>
      <details className="mt-4 rounded-lg border border-border bg-background p-4">
        <summary className="cursor-pointer text-sm font-medium">Histórico da composição ({investigation.events.length})</summary>
        <ol className="mt-3 space-y-2 text-sm">
          {investigation.events.map((event) => <li key={`${event.sequence}-${event.signalId}`}><span className="font-medium">{event.action === 'add' ? 'Adicionado' : event.action === 'remove' ? 'Removido' : 'Rejeitado'}</span> · {event.signalId} · {event.actorId}</li>)}
        </ol>
      </details>
    </section>
  )
}

function ComparisonCard({ id, title, body, label }: { id: string; title: string; body: string; label: string }) {
  return <article className="rounded-lg border border-border bg-background p-4"><Badge variant="outline">{label}</Badge><h4 className="mt-2 font-medium">{title}</h4><p className="mt-2 line-clamp-5 text-sm leading-relaxed text-muted-foreground">{body}</p><p className="mt-3 font-mono text-[11px] text-muted-foreground">{id}</p></article>
}

function SuggestionState({ item }: { item: RelatedSignal }) {
  if (item.status === 'pending') return <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"><Clock3 className="size-3.5" aria-hidden /> Processamento em andamento</span>
  if (item.status === 'failed') return <span className="inline-flex items-center gap-1.5 text-xs text-destructive"><AlertTriangle className="size-3.5" aria-hidden /> Não foi possível preparar esta sugestão</span>
  return <span className="inline-flex items-center gap-1.5 text-xs text-andiroba"><CheckCircle2 className="size-3.5" aria-hidden /> Sugestão disponível</span>
}

function relatedHref(originId: string, candidateId: string, returnTo: string): string {
  const relatedReturn = `/sinais/${originId}?${new URLSearchParams({ tab: 'related', returnTo })}`
  return `/sinais/${candidateId}?${new URLSearchParams({ returnTo: relatedReturn })}`
}

function relationLabel(value: string | null): string {
  const labels: Record<string, string> = { duplicate: 'Possível duplicata', corroborates: 'Possível corroboração', updates: 'Possível atualização', related_context: 'Contexto possivelmente relacionado', unrelated: 'Provavelmente não relacionado' }
  return value ? labels[value] ?? value : 'Relação não informada'
}

function normalizeInvestigation(value: ReadInvestigationDetail | null): InvestigationDetail | null {
  if (!value) return null
  return {
    id: value.id,
    version: value.version,
    createdAt: value.createdAt,
    updatedAt: value.updatedAt,
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
