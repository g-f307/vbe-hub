"use client";

import Link from "next/link";
import Image from "next/image";
import { BarChart3, LogOut, MapPinned, RadioTower } from "lucide-react";
import { Button } from "@/v0/components/ui/button";

export function Header() {
  return (
    <header className="bg-primary text-primary-foreground shadow-[0_8px_24px_-18px_rgba(18,50,69,0.85)]">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex min-h-20 items-center justify-between gap-4 py-3 sm:min-h-24">
          <Link href="/" aria-label="VBE Hub — início" className="flex min-w-0 items-center gap-4 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary">
            <Image
              src="/brand/vbehub-horizontal-fundo-escuro.svg"
              width="154"
              height="70"
              alt="VBE Hub"
              className="h-14 w-auto shrink-0 sm:h-16"
              priority
            />
            <span className="hidden border-l border-white/25 pl-4 text-xs leading-snug text-white/75 lg:block">
              Hub de Vigilância Baseada em Eventos
            </span>
          </Link>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <span className="hidden rounded-md border border-white/25 bg-white/5 px-2.5 py-1 text-xs text-white/80 md:inline-flex">
              Dados locais de demonstração
            </span>
            <Button
              aria-label="Sair do ambiente de demonstração"
              variant="ghost"
              size="sm"
              className="text-white/80 hover:bg-white/10 hover:text-white"
            >
              <LogOut className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Sair</span>
            </Button>
          </div>
        </div>

        <nav aria-label="Visões do sistema" className="flex min-h-12 items-end gap-1 overflow-x-auto border-t border-white/15">
          <HeaderLink href="/" icon={RadioTower}>Detectados</HeaderLink>
          <HeaderLink href="/panorama" icon={MapPinned}>Visão geoespacial</HeaderLink>
          <span
            aria-disabled="true"
            title="Implementação futura"
            className="inline-flex min-h-12 shrink-0 cursor-not-allowed items-center gap-2 border-b-2 border-transparent px-3 text-sm font-medium text-white/45"
          >
            <BarChart3 className="size-4" aria-hidden />
            Indicadores
            <span className="rounded-sm border border-white/20 px-1.5 py-0.5 text-[10px]">Implementação futura</span>
          </span>
        </nav>
      </div>
    </header>
  );
}

function HeaderLink({ href, icon: Icon, children }: { href: string; icon: typeof RadioTower; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex min-h-12 shrink-0 items-center gap-2 border-b-2 border-transparent px-3 text-sm font-medium text-white/80 hover:border-[#BFE6F7] hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-white"
    >
      <Icon className="size-4" aria-hidden />
      {children}
    </Link>
  )
}

