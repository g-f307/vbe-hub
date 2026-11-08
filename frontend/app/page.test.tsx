import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import Home from './page'

describe('fundação visual aprovada', () => {
  it('renderiza o código do protótipo com as três visualizações principais', () => {
    let html = ''
    try {
      html = renderToStaticMarkup(<Home />)
    } catch {
      // A fundação anterior redireciona a raiz e, portanto, não produz a interface aprovada.
    }

    expect(html).toContain('Hub de Vigilância Epidemiológica')
    expect(html).toContain('Fluxo de Trabalho')
    expect(html).toContain('Visão Geoespacial')
    expect(html).toContain('Indicadores')
    expect(html).toContain('Dados locais de demonstração')
    expect(html).toContain('aria-pressed="true"')
  })
})
