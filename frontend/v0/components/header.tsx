"use client";

import { Activity, LogOut } from "lucide-react";
import { Button } from "@/v0/components/ui/button";

export function Header() {
  return (
    <header className="bg-primary text-primary-foreground shadow-lg">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-foreground/10">
              <Activity className="w-6 h-6" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg leading-tight">VBEHub</span>
              <span className="text-xs text-primary-foreground/70 hidden sm:block">
                Hub de Vigilância Epidemiológica
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <span className="hidden rounded-md border border-primary-foreground/30 px-2.5 py-1 text-xs text-primary-foreground/85 md:inline-flex">
              Dados locais de demonstração
            </span>
            <Button
              aria-label="Sair do ambiente de demonstração"
              variant="ghost"
              size="sm"
              className="text-primary-foreground hover:bg-primary-foreground/10"
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

