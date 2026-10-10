import Link from 'next/link'
import { SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function SignalNotFound() {
  return <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4 px-4 py-12 md:px-6"><div className="rounded-md border border-agua bg-mineral p-5"><SearchX className="size-6 text-ardosia" aria-hidden /><h1 className="mt-3 text-lg font-semibold text-encontro">Sinal não encontrado</h1><p className="mt-1 text-sm leading-relaxed text-grafite">O identificador não existe na consulta atual ou o sinal não está acessível. Nenhum conteúdo foi inventado para esta tela.</p><Button className="mt-4" render={<Link href="/triagem" />} nativeButton={false}>Voltar para a triagem</Button></div></div>
}
