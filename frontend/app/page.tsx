"use client";

import { useState, useMemo } from "react";
import { Header } from "@/v0/components/header";
import { FiltersBar } from "@/v0/components/filters-bar";
import { KanbanBoard } from "@/v0/components/kanban-board";
import { IndicatorsView } from "@/v0/components/indicators-view";
import { SignalDetailModal } from "@/v0/components/signal-detail-modal";
import dynamic from "next/dynamic";
import { SignalFormModal, type SignalFormData } from "@/v0/components/signal-form-modal";
import { DeleteConfirmDialog } from "@/v0/components/delete-confirm-dialog";
import { useSignals, createSignal, updateSignal, deleteSignal } from "@/v0/lib/signals-store";
import type { Signal, RiskLevel, SignalSource } from "@/v0/lib/types";
import { Loader2, LayoutGrid, Map, BarChart3 } from "lucide-react";
import { cn } from "@/v0/lib/utils";

const MapView = dynamic(
  () => import("@/v0/components/map-view").then((mod) => mod.MapView),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[500px] w-full items-center justify-center bg-muted/20 rounded-lg border border-border">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }
);


type ViewType = "kanban" | "map" | "indicators";

export default function Home() {
  const { signals, isLoading } = useSignals();

  // View state
  const [activeView, setActiveView] = useState<ViewType>("kanban");

  // Filter states
  const [filterSource, setFilterSource] = useState<SignalSource | "all">("all");
  const [filterRisk, setFilterRisk] = useState<RiskLevel | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal states
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [signalToDelete, setSignalToDelete] = useState<Signal | null>(null);

  // Filtered signals based on search
  const filteredSignals = useMemo(() => {
    if (!searchQuery.trim()) return signals;

    const query = searchQuery.toLowerCase();
    return signals.filter(
      (signal) =>
        signal.title.toLowerCase().includes(query) ||
        signal.description.toLowerCase().includes(query) ||
        signal.municipalities.some((m) => m.toLowerCase().includes(query)) ||
        signal.states.some((s) => s.toLowerCase().includes(query)) ||
        signal.tags.some((t) => t.toLowerCase().includes(query))
    );
  }, [signals, searchQuery]);

  // Handlers
  const handleSignalClick = (signal: Signal) => {
    setSelectedSignal(signal);
    setDetailModalOpen(true);
  };

  const handleNewSignal = () => {
    setSelectedSignal(null);
    setFormMode("create");
    setFormModalOpen(true);
  };

  const handleEditSignal = (signal: Signal) => {
    setSelectedSignal(signal);
    setDetailModalOpen(false);
    setFormMode("edit");
    setFormModalOpen(true);
  };

  const handleDeleteClick = (signal: Signal) => {
    setSignalToDelete(signal);
    setDetailModalOpen(false);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (signalToDelete) {
      await deleteSignal(signalToDelete.id);
      setSignalToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handleSaveSignal = async (data: SignalFormData) => {
    if (formMode === "create") {
      await createSignal({
        ...data,
        signalDate: new Date(data.signalDate).toISOString(),
        detectionDate: new Date(data.detectionDate).toISOString(),
        notificationDate: data.notificationDate
          ? new Date(data.notificationDate).toISOString()
          : undefined,
      });
    } else if (selectedSignal) {
      await updateSignal(selectedSignal.id, {
        ...data,
        signalDate: new Date(data.signalDate).toISOString(),
        detectionDate: new Date(data.detectionDate).toISOString(),
        notificationDate: data.notificationDate
          ? new Date(data.notificationDate).toISOString()
          : undefined,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Carregando sinais...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main id="conteudo-principal" className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* View Tabs */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex bg-card border border-border rounded-lg p-1 shadow-sm">
            <button
              type="button"
              aria-pressed={activeView === "kanban"}
              onClick={() => setActiveView("kanban")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                activeView === "kanban"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <LayoutGrid className="h-4 w-4" />
              <span className="hidden sm:inline">Fluxo de Trabalho</span>
              <span className="sm:hidden">Kanban</span>
            </button>
            <button
              type="button"
              aria-pressed={activeView === "map"}
              onClick={() => setActiveView("map")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                activeView === "map"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <Map className="h-4 w-4" />
              <span className="hidden sm:inline">Visão Geoespacial</span>
              <span className="sm:hidden">Mapa</span>
            </button>
            <button
              type="button"
              aria-pressed={activeView === "indicators"}
              onClick={() => setActiveView("indicators")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                activeView === "indicators"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Indicadores</span>
              <span className="sm:hidden">BI</span>
            </button>
          </div>
        </div>

        {/* Kanban View */}
        {activeView === "kanban" && (
          <>
            {/* Page Title */}
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-foreground">Fluxo de Trabalho</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Gerencie os sinais de surtos captados de diversas fontes
              </p>
            </div>

            {/* Filters */}
            <FiltersBar
              filterSource={filterSource}
              filterRisk={filterRisk}
              searchQuery={searchQuery}
              onFilterSourceChange={setFilterSource}
              onFilterRiskChange={setFilterRisk}
              onSearchChange={setSearchQuery}
              onNewSignal={handleNewSignal}
            />

            {/* Kanban Board */}
            <KanbanBoard
              signals={filteredSignals}
              onSignalClick={handleSignalClick}
              filterSource={filterSource}
              filterRisk={filterRisk}
            />

            {/* Stats Footer */}
            <div className="mt-6 pt-4 border-t border-border">
              <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                <span>
                  Total de sinais: <strong className="text-foreground">{signals.length}</strong>
                </span>
                {(filterSource !== "all" || filterRisk !== "all" || searchQuery) && (
                  <span>
                    Exibindo: <strong className="text-foreground">{filteredSignals.length}</strong>
                  </span>
                )}
              </div>
            </div>
          </>
        )}

        {/* Map View */}
        {activeView === "map" && (
          <MapView signals={signals} onSignalClick={handleSignalClick} />
        )}

        {/* Indicators View */}
        {activeView === "indicators" && (
          <IndicatorsView signals={signals} />
        )}
      </main>

      {/* Modals */}
      <SignalDetailModal
        signal={selectedSignal}
        open={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        onEdit={handleEditSignal}
        onDelete={handleDeleteClick}
      />

      <SignalFormModal
        signal={selectedSignal}
        open={formModalOpen}
        onClose={() => setFormModalOpen(false)}
        onSave={handleSaveSignal}
        mode={formMode}
      />

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleConfirmDelete}
        title={signalToDelete?.title || ""}
      />
    </div>
  );
}
