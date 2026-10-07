import Link from 'next/link'

import { AppShell } from '@/components/app-shell'
import { PanelStateMessage } from '@/components/panel-state'
import { resolvePanelState } from '@/lib/panel-state'

type PanoramaPageProps = {
  searchParams: Promise<{ estado?: string }>
}

export default async function PanoramaPage({ searchParams }: PanoramaPageProps) {
  const { estado } = await searchParams
  const state = resolvePanelState(estado)

  return (
    <AppShell active="panorama">
      <header className="topbar">
        <div>
          <p className="eyebrow">Leitura territorial</p>
          <p className="topbar-title">Panorama</p>
        </div>
        <span className="demo-badge"><i /> Sem precisão residencial</span>
      </header>
      <section className="page-intro">
        <p className="eyebrow">03 · Contexto</p>
        <h1>Panorama espacial</h1>
        <p>Base para uma visualização agregada por área, construída com preservação de privacidade.</p>
      </section>
      <PanelStateMessage state={state} subject="Estado do panorama" />
      {state === 'ready' && (
        <section className="map-foundation" aria-label="Estrutura do futuro panorama espacial">
          <div className="map-grid" aria-hidden="true">
            <span className="map-node node-one" /><span className="map-node node-two" />
            <span className="map-node node-three" /><span className="map-node node-four" />
          </div>
          <div className="map-copy">
            <p className="eyebrow">Antes de adicionar um mapa</p>
            <h2>A visualização mostrará agregados, nunca a localização exata de um relato.</h2>
            <p>A próxima fase definirá limites territoriais, regras de supressão e uma legenda auditável.</p>
            <Link className="quiet-link" href="?estado=vazio">Ver estado sem agregados</Link>
          </div>
        </section>
      )}
    </AppShell>
  )
}
