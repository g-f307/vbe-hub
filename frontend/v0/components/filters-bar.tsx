"use client";

import { Filter, Plus, Search, X } from "lucide-react";
import { Button } from "@/v0/components/ui/button";
import { Input } from "@/v0/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/v0/components/ui/select";
import type { RiskLevel, SignalSource } from "@/v0/lib/types";

interface FiltersBarProps {
  filterSource: SignalSource | "all";
  filterRisk: RiskLevel | "all";
  searchQuery: string;
  onFilterSourceChange: (value: SignalSource | "all") => void;
  onFilterRiskChange: (value: RiskLevel | "all") => void;
  onSearchChange: (value: string) => void;
  onNewSignal: () => void;
}

const SOURCES: { value: SignalSource | "all"; label: string }[] = [
  { value: "all", label: "Todas as Fontes" },
  { value: "EIOS", label: "EIOS" },
  { value: "Guardiões da Saúde", label: "Guardiões da Saúde" },
  { value: "Twitter/X", label: "Twitter/X" },
  { value: "Facebook", label: "Facebook" },
  { value: "WhatsApp", label: "WhatsApp" },
  { value: "Jornal", label: "Jornal" },
  { value: "Portal de Notícias", label: "Portal de Notícias" },
  { value: "Unidade de Saúde", label: "Unidade de Saúde" },
  { value: "Outro", label: "Outro" },
];

const RISK_LEVELS: { value: RiskLevel | "all"; label: string }[] = [
  { value: "all", label: "Todos os Níveis" },
  { value: "alto", label: "Alto" },
  { value: "medio", label: "Médio" },
  { value: "baixo", label: "Baixo" },
];

export function FiltersBar({
  filterSource,
  filterRisk,
  searchQuery,
  onFilterSourceChange,
  onFilterRiskChange,
  onSearchChange,
  onNewSignal,
}: FiltersBarProps) {
  const hasActiveFilters = filterSource !== "all" || filterRisk !== "all" || searchQuery !== "";

  const clearFilters = () => {
    onFilterSourceChange("all");
    onFilterRiskChange("all");
    onSearchChange("");
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 mb-6 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        {/* Left side: Filters label and filters */}
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Filter className="w-4 h-4" />
          <span>Filtros:</span>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row flex-1 gap-3">
          {/* Source Filter */}
          <Select value={filterSource} onValueChange={onFilterSourceChange}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Fonte" />
            </SelectTrigger>
            <SelectContent>
              {SOURCES.map((source) => (
                <SelectItem key={source.value} value={source.value}>
                  {source.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Risk Level Filter */}
          <Select value={filterRisk} onValueChange={onFilterRiskChange}>
            <SelectTrigger className="w-full sm:w-[160px]">
              <SelectValue placeholder="Nível de Risco" />
            </SelectTrigger>
            <SelectContent>
              {RISK_LEVELS.map((risk) => (
                <SelectItem key={risk.value} value={risk.value}>
                  {risk.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              aria-label="Buscar sinais"
              placeholder="Buscar sinais…"
              className="pl-9"
            />
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4 mr-1" />
              Limpar
            </Button>
          )}
        </div>

        {/* Right side: New Signal button */}
        <Button onClick={onNewSignal} className="w-full sm:w-auto">
          <Plus className="w-4 h-4 mr-2" />
          Novo Sinal
        </Button>
      </div>
    </div>
  );
}

