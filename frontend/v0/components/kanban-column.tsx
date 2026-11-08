"use client";

import React from "react"

import { useState } from "react";
import type { Signal, SignalStatus } from "@/v0/lib/types";
import { STATUS_CONFIG } from "@/v0/lib/types";
import { SignalCard } from "./signal-card";
import { cn } from "@/v0/lib/utils";

interface KanbanColumnProps {
  status: SignalStatus;
  signals: Signal[];
  onSignalClick: (signal: Signal) => void;
  onDragStart: (e: React.DragEvent, signal: Signal) => void;
  onDrop: (status: SignalStatus) => void;
  onDragOver: (e: React.DragEvent) => void;
}

export function KanbanColumn({
  status,
  signals,
  onSignalClick,
  onDragStart,
  onDrop,
  onDragOver,
}: KanbanColumnProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const config = STATUS_CONFIG[status];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
    onDragOver(e);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    onDrop(status);
  };

  return (
    <div className="flex flex-col min-w-[300px] max-w-[320px] flex-shrink-0 lg:flex-1 lg:min-w-0 lg:max-w-none">
      {/* Column Header */}
      <div className="mb-3">
        <div className={cn("h-1.5 rounded-full mb-3", config.color)} />
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm text-foreground">{config.title}</h3>
          <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-1 rounded-full">
            {signals.length}
          </span>
        </div>
      </div>

      {/* Cards Container */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "kanban-column flex flex-col gap-3 p-3 rounded-lg transition-colors",
          config.bgColor,
          isDragOver && "ring-2 ring-primary ring-offset-2"
        )}
      >
        {signals.length === 0 ? (
          <div className="flex items-center justify-center h-24 text-sm text-muted-foreground">
            Nenhum sinal
          </div>
        ) : (
          signals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              onClick={() => onSignalClick(signal)}
              onDragStart={onDragStart}
            />
          ))
        )}
      </div>
    </div>
  );
}

