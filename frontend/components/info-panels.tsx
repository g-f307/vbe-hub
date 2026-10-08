'use client'

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { EXTRACTION_VERSION } from '@/lib/mock-data'

const METHOD_STEPS = [
  {
    title: 'Coleta',
    text: 'Registros sintéticos de notícias e relatos comunitários são recebidos em lotes.',
  },
  {
    title: 'Extração',
    text: 'Um extrator identifica condição ou síndrome mencionada, sintomas, local, período e magnitude. Campos ausentes são marcados como “Não informado”.',
  },
  {
    title: 'Aproximação',
    text: 'Pares de registros são comparados por sintomas, área geográfica, período e independência das fontes.',
  },
  {
    title: 'Consolidação',
    text: 'Registros relacionados formam um sinal com prioridade sugerida, sempre sujeito à revisão humana.',
  },
  {
    title: 'Decisão',
    text: 'A vigilância aceita, corrige ou rejeita o agrupamento e define o próximo estado. Toda decisão fica na trilha de auditoria.',
  },
]

const LIMITS = [
  'A IA não confirma surtos, doenças ou emergências.',
  'A confiança indica similaridade entre registros, não probabilidade de evento real.',
  'Magnitudes vêm do texto das fontes e podem divergir.',
  'Todos os dados desta demonstração são sintéticos.',
]

export function MethodSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Método e limites</SheetTitle>
          <SheetDescription>Como o VBE Hub organiza evidências para a vigilância.</SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-6 px-4 pb-6">
          <ol className="flex flex-col">
            {METHOD_STEPS.map((step, index) => (
              <li key={step.title} className="relative flex gap-3 pb-4 last:pb-0">
                <div className="flex flex-col items-center">
                  <span className="mt-1 size-2.5 shrink-0 rounded-full border-2 border-igarape bg-mineral" aria-hidden />
                  {index < METHOD_STEPS.length - 1 && <span className="mt-1 w-px flex-1 bg-agua-strong" aria-hidden />}
                </div>
                <div>
                  <p className="text-sm font-semibold text-encontro">{step.title}</p>
                  <p className="text-sm leading-relaxed text-ardosia">{step.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <section aria-labelledby="limites-title" className="rounded-md border border-andiroba/50 bg-andiroba-soft p-3">
            <h3 id="limites-title" className="text-sm font-semibold text-andiroba-ink">
              Limites
            </h3>
            <ul className="mt-2 flex list-disc flex-col gap-1 pl-4 text-sm text-grafite">
              {LIMITS.map((limit) => (
                <li key={limit}>{limit}</li>
              ))}
            </ul>
          </section>
          <p className="text-xs text-ardosia">
            Versão do extrator: <span className="font-mono">{EXTRACTION_VERSION}</span>
          </p>
        </div>
      </SheetContent>
    </Sheet>
  )
}

const HELP_ITEMS = [
  { term: 'Prioridade sugerida', text: 'Ordenação proposta pelo sistema. Não substitui a avaliação da vigilância.' },
  { term: 'Fio de evidência', text: 'Mostra como cada registro se liga ao sinal consolidado e à decisão humana.' },
  { term: 'Confiança', text: 'Grau de similaridade entre registros. Não indica confirmação do evento.' },
  { term: 'Navegação', text: 'Use Tab para percorrer controles e Enter ou Espaço para ativá-los.' },
]

export function HelpDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Ajuda</DialogTitle>
          <DialogDescription>Termos usados no VBE Hub.</DialogDescription>
        </DialogHeader>
        <dl className="flex flex-col gap-3">
          {HELP_ITEMS.map((item) => (
            <div key={item.term}>
              <dt className="text-sm font-semibold text-encontro">{item.term}</dt>
              <dd className="text-sm leading-relaxed text-ardosia">{item.text}</dd>
            </div>
          ))}
        </dl>
      </DialogContent>
    </Dialog>
  )
}
