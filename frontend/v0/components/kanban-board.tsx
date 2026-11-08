"use client";

import React from "react"

import { useState, useCallback } from "react";
import type { Signal, SignalStatus, RiskLevel, SignalSource } from "@/v0/lib/types";
import { STATUS_CONFIG } from "@/v0/lib/types";
import { KanbanColumn } from "./kanban-column";
import { moveSignal, getSignalsByStatus } from "@/v0/lib/signals-store";

interface KanbanBoardProps {
  signals: Signal[];
  onSignalClick: (signal: Signal) => void;
  filterSource: SignalSource | "all";
  filterRisk: RiskLevel | "all";
}

const COLUMN_ORDER: SignalStatus[] = [
  "informado",
  "em_analise",
  "em_monitoramento",
  "evento_confirmado",
  "descartado",
];

export function KanbanBoard({ signals, onSignalClick, filterSource, filterRisk }: KanbanBoardProps) {
  const [draggedSignal, setDraggedSignal] = useState<Signal | null>(null);

  const filteredSignals = signals.filter((signal) => {
    if (filterSource !== "all" && signal.source !== filterSource) return false;
    if (filterRisk !== "all" && signal.riskLevel !== filterRisk) return false;
    return true;
  });

  const handleDragStart = useCallback((e: React.DragEvent, signal: Signal) => {
    setDraggedSignal(signal);
    e.dataTransfer.setData("text/plain", signal.id);
    
    // Add visual feedback
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.classList.add("dragging");
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const handleDrop = useCallback(async (newStatus: SignalStatus) => {
    if (draggedSignal && draggedSignal.status !== newStatus) {
      await moveSignal(draggedSignal.id, newStatus);
    }
    setDraggedSignal(null);
  }, [draggedSignal]);

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 px-1">
      {COLUMN_ORDER.map((status) => (
        <KanbanColumn
          key={status}
          status={status}
          signals={getSignalsByStatus(filteredSignals, status)}
          onSignalClick={onSignalClick}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        />
      ))}
    </div>
  );
}

