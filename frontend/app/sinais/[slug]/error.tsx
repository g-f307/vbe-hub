'use client'

import Link from 'next/link'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function SignalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4 px-4 py-12 md:px-6"><div role="alert" className="rounded-md border border-urucum/40 bg-urucum-soft p-5"><AlertTriangle className="size-5 text-urucum-ink" aria-hidden /><h1 className="mt-3 text-lg font-semibold text-encontro">Não foi possível consultar este sinal</h1><p className="mt-1 text-sm leading-relaxed text-grafite">A investigação canônica está indisponível ou inválida. Nenhum conteúdo de demonstração foi usado como substituto.</p><div className="mt-4 flex flex-wrap gap-2"><Button onClick={reset}>Tentar novamente</Button><Button variant="outline" render={<Link href="/triagem" />} nativeButton={false}>Voltar para a triagem</Button></div></div></div>
}
