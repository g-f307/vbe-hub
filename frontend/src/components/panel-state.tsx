import Link from 'next/link'

import type { PanelState } from '@/lib/panel-state'

type PanelStateMessageProps = {
  state: PanelState
  subject: string
}

const copy: Record<Exclude<PanelState, 'ready'>, { title: string; detail: string }> = {
  loading: {
    title: 'Consultando a fila',
    detail: 'A área reserva este estado para buscas que ainda estão em andamento.',
  },
  empty: {
    title: 'Nada para mostrar neste recorte',
    detail: 'Quando houver registros compatíveis com os filtros, eles aparecerão aqui para revisão humana.',
  },
  unavailable: {
    title: 'Conexão indisponível',
    detail: 'A interface permanece segura: ela não inventa resultados quando a API não pode ser consultada.',
  },
}

export function PanelStateMessage({ state, subject }: PanelStateMessageProps) {
  if (state === 'ready') {
    return null
  }

  const message = copy[state]

  return (
    <section className="state-message" aria-live="polite">
      <span className="state-orb" aria-hidden="true" />
      <div>
        <p className="eyebrow">{subject}</p>
        <h2>{message.title}</h2>
        <p>{message.detail}</p>
      </div>
      <Link className="quiet-link" href="?estado=pronto">
        Voltar ao estado inicial
      </Link>
    </section>
  )
}
