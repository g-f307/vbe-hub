"use client";

import React from "react"

import { MapPin, Calendar, GripVertical } from "lucide-react";
import { Card } from "@/v0/components/ui/card";
import { Badge } from "@/v0/components/ui/badge";
import type { Signal } from "@/v0/lib/types";
import { RISK_CONFIG } from "@/v0/lib/types";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface SignalCardProps {
  signal: Signal;
  onClick: () => void;
  onDragStart: (e: React.DragEvent, signal: Signal) => void;
}

export function SignalCard({ signal, onClick, onDragStart }: SignalCardProps) {
  const riskConfig = RISK_CONFIG[signal.riskLevel];

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.effectAllowed = "move";
    onDragStart(e, signal);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <Card
      role="button"
      tabIndex={0}
      aria-label={`Abrir sinal ${signal.title}`}
      draggable
      onDragStart={handleDragStart}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      className="signal-card p-4 cursor-pointer bg-card hover:bg-accent/50 border border-border group"
    >
      <div className="flex items-start gap-2">
        <div className="opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing">
          <GripVertical className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h4 className="font-medium text-sm text-card-foreground line-clamp-2 mb-2">
            {signal.title}
          </h4>

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-1.5 mb-3">
            <Badge className={`${riskConfig.bgColor} ${riskConfig.color} text-xs px-2 py-0.5`}>
              {riskConfig.label}
            </Badge>
            <Badge variant="outline" className="text-xs px-2 py-0.5 bg-card">
              {signal.source}
            </Badge>
          </div>

          {/* Description */}
          <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
            {signal.description}
          </p>

          {/* Footer */}
          <div className="flex flex-col gap-1.5 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <MapPin className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">
                {signal.municipalities[0] || signal.states[0] || signal.countries[0]}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3 flex-shrink-0" />
              <span>
                {format(new Date(signal.detectionDate), "dd/MM/yyyy HH:mm", { locale: ptBR })}
              </span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

