"use client";

import Link from "next/link";
import Image from "next/image";
import { LogOut } from "lucide-react";
import { Button } from "@/v0/components/ui/button";

export function Header() {
  return (
    <header className="border-b border-border bg-card text-foreground shadow-[0_1px_0_rgba(18,50,69,0.03)]">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex min-h-18 items-center justify-between gap-4 py-2">
          <Link href="/" aria-label="VBE Hub — início" className="flex min-w-0 items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
            <Image
              src="/brand/vbehub-horizontal-fundo-claro.svg"
              width="132"
              height="60"
              alt="VBE Hub"
              className="h-12 w-auto shrink-0"
            />
            <span className="hidden border-l border-border pl-3 text-xs leading-snug text-muted-foreground lg:block">
              Hub de Vigilância Baseada em Eventos
            </span>
          </Link>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <span className="hidden rounded-md border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground md:inline-flex">
              Dados locais de demonstração
            </span>
            <Button
              aria-label="Sair do ambiente de demonstração"
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              <LogOut className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Sair</span>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}

