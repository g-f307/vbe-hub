import Link from 'next/link'

import { AppShell } from '@/components/app-shell'
import { PanelStateMessage } from '@/components/panel-state'
import { resolvePanelState } from '@/lib/panel-state'

type SignalPageProps = {
  params: Promise<{ signalId: string }>
  searchParams: Promise<{ estado?: string }>
}

export default async function SignalPage({ params, searchParams }: SignalPageProps) {
  const [{ signalId }, { estado }] = await Promise.all([params, searchParams])
  const state = resolvePanelState(estado)

  return (
    <AppShell active="sinal">
      <header className="topbar">
        <Link className="back-link" href="/triagem">← Voltar à triagem</Link>
        <span className="demo-badge"><i /> Estrutura em evolução</span>
      </header>
      <section className="page-intro">
        <p className="eyebrow">02 · Investigação</p>
        <h1>Ficha técnica</h1>
        <p>Rota preparada para o sinal <code>{signalId}</code>, sem fabricar evidências antes da integração.</p>
      </section>
      <PanelStateMessage state={state} subject="Estado da ficha" />
      {state === 'ready' && (
        <section className="record-layout" aria-label="Estrutura da ficha técnica">
          <article className="record-core">
            <p className="eyebrow">Leitura orientada à evidência</p>
            <h2>O que a revisão humana poderá verificar</h2>
            <dl className="record-list">
              <div><dt>Resumo do sinal</dt><dd>Descrição consolidada e indicação explícita de incerteza.</dd></div>
              <div><dt>Registros de origem</dt><dd>Vínculos rastreáveis para cada evidência usada na correlação.</dd></div>
              <div><dt>Contexto</dt><dd>Tempo, lugar e condição em campos verificáveis.</dd></div>
              <div><dt>Decisão</dt><dd>Justificativa e ação do profissional; a IA apenas sugere.</dd></div>
            </dl>
          </article>
          <aside className="audit-note">
            <p className="eyebrow">Princípio do produto</p>
            <p>Não há classificação definitiva, prioridade clínica ou diagnóstico nesta tela.</p>
          </aside>
        </section>
      )}
    </AppShell>
  )
}
