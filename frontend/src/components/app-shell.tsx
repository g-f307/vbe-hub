import Link from 'next/link'
import type { ReactNode } from 'react'

type AppShellProps = {
  active: 'triagem' | 'sinal' | 'panorama'
  children: ReactNode
}

const navigation = [
  { href: '/triagem', label: 'Triagem', key: 'triagem', glyph: '⌁' },
  { href: '/sinais/exemplo', label: 'Ficha técnica', key: 'sinal', glyph: '□' },
  { href: '/panorama', label: 'Panorama', key: 'panorama', glyph: '◌' },
] as const

export function AppShell({ active, children }: AppShellProps) {
  return (
    <div className="app-frame">
      <a className="skip-link" href="#conteudo-principal">
        Ir para o conteúdo principal
      </a>
      <aside className="rail" aria-label="Navegação principal">
        <Link className="brand" href="/triagem" aria-label="VBE Hub, ir para triagem">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span className="brand-name">VBE<br />Hub</span>
        </Link>
        <nav>
          <ul className="rail-list">
            {navigation.map((item) => (
              <li key={item.key}>
                <Link
                  className={item.key === active ? 'rail-link is-active' : 'rail-link'}
                  href={item.href}
                  aria-current={item.key === active ? 'page' : undefined}
                >
                  <span aria-hidden="true">{item.glyph}</span>
                  <span>{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <p className="rail-note">PoC · decisão humana</p>
      </aside>
      <main id="conteudo-principal" className="workspace">
        {children}
      </main>
    </div>
  )
}
