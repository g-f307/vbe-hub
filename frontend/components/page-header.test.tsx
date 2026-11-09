import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { PageHeader } from './page-header'

describe('PageHeader', () => {
  it('aplica a escala tipográfica do contrato visual aos títulos de página', () => {
    const html = renderToStaticMarkup(
      <PageHeader title="Panorama territorial" description="Descrição operacional" meta="Metadado" />,
    )

    expect(html).toContain('text-[26px]')
    expect(html).toContain('text-[13px]')
    expect(html).toContain('text-xs')
  })
})
