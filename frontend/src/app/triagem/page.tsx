import Link from 'next/link'

import { AppShell } from '@/components/app-shell'
import { PanelStateMessage } from '@/components/panel-state'
import { resolvePanelState } from '@/lib/panel-state'

type TriagePageProps = {
  searchParams: Promise<{ estado?: string }>
}

export default async function TriagePage({ searchParams }: TriagePageProps) {
  const { estado } = await searchParams
  const state = resolvePanelState(estado)

  return (
    <AppShell active="triagem">
      <header className="topbar">
        <div>
          <p className="eyebrow">Central de revisão</p>
          <p className="topbar-title">Triagem</p>
        </div>
        <span className="demo-badge"><i /> Ambiente de demonstração</span>
      </header>
      <section className="page-intro">
        <p className="eyebrow">01 · Entrada</p>
        <h1>Sinais para triagem</h1>
        <p>Uma fila para situar evidências, não uma confirmação automática de evento.</p>
      </section>
      <PanelStateMessage state={state} subject="Estado da fila" />
      {state === 'ready' && (
        <section className="foundation-grid" aria-label="Fundação da fila de triagem">
          <article className="signal-panel signal-panel--primary">
            <p className="eyebrow">Próxima entrega</p>
            <h2>A fila será conectada ao fluxo já validado no backend.</h2>
            <p>
              Cada sinal manterá seus registros de origem, o contexto extraído e a indicação de que a decisão final cabe à vigilância.
            </p>
            <div className="field-ribbon" aria-label="Campos previstos para o cartão de sinal">
              <span>origem</span><span>localização</span><span>período</span><span>condição</span>
            </div>
          </article>
          <article className="signal-panel signal-panel--aside">
            <p className="eyebrow">Interface verificável</p>
            <h2>Estados previstos</h2>
            <div className="state-links">
              <Link href="?estado=carregando">Carregando</Link>
              <Link href="?estado=vazio">Sem resultados</Link>
              <Link href="?estado=indisponivel">Indisponível</Link>
            </div>
          </article>
        </section>
      )}
    </AppShell>
  )
}
