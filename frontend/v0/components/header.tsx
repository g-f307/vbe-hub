"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { BarChart3, LogOut, MapPinned, RadioTower } from "lucide-react";
import { Button } from "@/v0/components/ui/button";

export function Header() {
  const pathname = usePathname() ?? "";
  const detectedActive = pathname === "/" || pathname.startsWith("/sinais/");
  const panoramaActive = pathname.startsWith("/panorama");

  return (
    <header className="bg-[var(--brand-blue)] pb-6 text-white shadow-sm">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex min-h-20 items-center justify-between gap-4 py-3 sm:min-h-24">
          <Link href="/" aria-label="VBE Hub — início" className="flex min-w-0 items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary">
            <Image
              src="/brand/vbehub-horizontal-fundo-escuro.svg"
              width="154"
              height="70"
              alt="VBE Hub"
              className="h-14 w-auto shrink-0 sm:h-16"
              priority
            />
          </Link>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button
              aria-label="Sair do ambiente de demonstração"
              variant="ghost"
              size="sm"
              className="border border-white/35 text-[15px] font-semibold text-white [text-shadow:0_1px_1px_rgba(8,54,83,0.24)] hover:border-white/60 hover:bg-white/10 hover:text-white focus-visible:ring-white"
            >
              <LogOut className="size-[18px] mr-2" strokeWidth={2.25} aria-hidden />
              <span className="hidden sm:inline">Sair</span>
            </Button>
          </div>
        </div>

        <nav aria-label="Visões do sistema" className="flex min-h-12 items-end justify-center gap-1 overflow-x-auto border-t border-white/15 px-2 [text-shadow:0_1px_1px_rgba(8,54,83,0.24)]">
          <HeaderLink href="/" icon={RadioTower} active={detectedActive}>Detectados</HeaderLink>
          <HeaderLink href="/panorama" icon={MapPinned} active={panoramaActive}>Visão geoespacial</HeaderLink>
          <span
            aria-disabled="true"
            className="inline-flex min-h-12 shrink-0 cursor-not-allowed items-center gap-2 border-b-[3px] border-transparent px-3 text-[15px] font-semibold text-white/70"
          >
            <BarChart3 className="size-[18px]" strokeWidth={2.25} aria-hidden />
            Indicadores
          </span>
        </nav>
      </div>
    </header>
  );
}

function HeaderLink({ href, icon: Icon, active, children }: { href: string; icon: typeof RadioTower; active: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`inline-flex min-h-12 shrink-0 items-center gap-2 border-b-[3px] px-3 text-[15px] font-semibold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-white ${active ? "border-white" : "border-transparent hover:border-white/60"}`}
    >
      <Icon className="size-[18px]" strokeWidth={2.25} aria-hidden />
      {children}
    </Link>
  )
}

