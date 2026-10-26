'use client'

import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function WorkflowError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4 px-4 py-12 md:px-6">
      <div role="alert" className="rounded-md border border-urucum/40 bg-urucum-soft p-5">
        <AlertTriangle className="size-5 text-urucum-ink" aria-hidden />
        <h1 className="mt-3 text-lg font-semibold text-encontro">Não foi possível consultar o fluxo dos sinais</h1>
        <p className="mt-1 text-sm leading-relaxed text-grafite">A API canônica está indisponível ou a leitura mudou durante a atualização. Recarregue para obter o estado atual; nenhum dado mockado será usado como substituto.</p>
        <Button className="mt-4" onClick={reset}><RefreshCw aria-hidden />Recarregar dados canônicos</Button>
      </div>
    </div>
  )
}
