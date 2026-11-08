"use client";

import React from "react"

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/v0/components/ui/dialog";
import { Button } from "@/v0/components/ui/button";
import { Badge } from "@/v0/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/v0/components/ui/tabs";
import {
  AlertTriangle,
  Calendar,
  MapPin,
  FileText,
  Tag,
  Shield,
  Clock,
  Building,
  Globe,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import type { Signal } from "@/v0/lib/types";
import { RISK_CONFIG, STATUS_CONFIG } from "@/v0/lib/types";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface SignalDetailModalProps {
  signal: Signal | null;
  open: boolean;
  onClose: () => void;
  onEdit: (signal: Signal) => void;
  onDelete: (signal: Signal) => void;
}

export function SignalDetailModal({
  signal,
  open,
  onClose,
  onEdit,
  onDelete,
}: SignalDetailModalProps) {
  if (!signal) return null;

  const riskConfig = RISK_CONFIG[signal.riskLevel];
  const statusConfig = STATUS_CONFIG[signal.status];

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR });
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader className="pb-4 border-b">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <DialogTitle className="text-xl font-semibold text-foreground mb-3">
                {signal.title}
              </DialogTitle>
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={`${riskConfig.bgColor} ${riskConfig.color}`}>
                  Risco {riskConfig.label}
                </Badge>
                <Badge variant="outline">{signal.source}</Badge>
                <Badge variant="secondary">{statusConfig.title}</Badge>
              </div>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="info" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="info" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Informações
            </TabsTrigger>
            <TabsTrigger value="location" className="flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Localização
            </TabsTrigger>
          </TabsList>

          <TabsContent value="info" className="mt-6 space-y-6">
            {/* Description */}
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Descrição</h4>
              <p className="text-sm text-foreground">{signal.description}</p>
            </div>

            {/* Signal Details Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <InfoItem
                icon={<Shield className="w-4 h-4" />}
                label="Confidencialidade"
                value={signal.confidentiality}
              />
              <InfoItem
                icon={<FileText className="w-4 h-4" />}
                label="Tipo de Sinal"
                value={signal.signalType}
              />
              <InfoItem
                icon={<AlertTriangle className="w-4 h-4" />}
                label="Etiologia"
                value={signal.etiology || "Não informado"}
              />
              <InfoItem
                icon={<AlertTriangle className="w-4 h-4" />}
                label="Perigo Geral"
                value={signal.generalDanger || "Não informado"}
              />
              <InfoItem
                icon={<AlertTriangle className="w-4 h-4" />}
                label="Perigo Específico"
                value={signal.specificDanger || "Não informado"}
              />
            </div>

            {/* Tags */}
            {signal.tags.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Tag className="w-4 h-4 text-muted-foreground" />
                  <h4 className="text-sm font-medium text-muted-foreground">Etiquetas</h4>
                </div>
                <div className="flex flex-wrap gap-2">
                  {signal.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Dates */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Datas
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <InfoItem
                  icon={<Calendar className="w-4 h-4" />}
                  label="Data do Sinal"
                  value={formatDate(signal.signalDate)}
                />
                <InfoItem
                  icon={<Calendar className="w-4 h-4" />}
                  label="Data de Detecção"
                  value={formatDate(signal.detectionDate)}
                />
                {signal.notificationDate && (
                  <InfoItem
                    icon={<Calendar className="w-4 h-4" />}
                    label="Data de Notificação"
                    value={formatDate(signal.notificationDate)}
                  />
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="location" className="mt-6 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <InfoItem
                icon={<Globe className="w-4 h-4" />}
                label="País(es)"
                value={signal.countries.join(", ") || "Não informado"}
              />
              <InfoItem
                icon={<Building className="w-4 h-4" />}
                label="Estado(s)"
                value={signal.states.join(", ") || "Não informado"}
              />
              <InfoItem
                icon={<MapPin className="w-4 h-4" />}
                label="Município(s)"
                value={signal.municipalities.join(", ") || "Não informado"}
              />
              <InfoItem
                icon={<Globe className="w-4 h-4" />}
                label="País de Origem"
                value={signal.originCountry || "Não informado"}
              />
            </div>

            {signal.address && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">Endereço</h4>
                <p className="text-sm text-foreground bg-muted p-3 rounded-md">
                  {signal.address}
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t mt-6">
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
          <Button
            variant="outline"
            onClick={() => onDelete(signal)}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Excluir
          </Button>
          <Button onClick={() => onEdit(signal)}>
            <Pencil className="w-4 h-4 mr-2" />
            Editar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function InfoItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-muted/50 p-3 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-muted-foreground">{icon}</span>
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>
      <p className="text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}

