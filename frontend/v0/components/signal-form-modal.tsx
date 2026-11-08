"use client";

import React from "react"

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/v0/components/ui/dialog";
import { Button } from "@/v0/components/ui/button";
import { Input } from "@/v0/components/ui/input";
import { Label } from "@/v0/components/ui/label";
import { Textarea } from "@/v0/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/v0/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/v0/components/ui/tabs";
import { FileText, MapPin, Loader2, X } from "lucide-react";
import { Badge } from "@/v0/components/ui/badge";
import type {
  Signal,
  RiskLevel,
  SignalStatus,
  SignalSource,
  SignalType,
  Confidentiality,
} from "@/v0/lib/types";

interface SignalFormModalProps {
  signal?: Signal | null;
  open: boolean;
  onClose: () => void;
  onSave: (data: SignalFormData) => Promise<void>;
  mode: "create" | "edit";
}

export interface SignalFormData {
  title: string;
  description: string;
  status: SignalStatus;
  riskLevel: RiskLevel;
  source: SignalSource;
  signalType: SignalType;
  confidentiality: Confidentiality;
  etiology: string;
  generalDanger: string;
  specificDanger: string;
  tags: string[];
  countries: string[];
  states: string[];
  municipalities: string[];
  originCountry: string;
  address: string;
  signalDate: string;
  detectionDate: string;
  notificationDate: string;
}

const SOURCES: SignalSource[] = [
  "EIOS",
  "Guardiões da Saúde",
  "Twitter/X",
  "Facebook",
  "WhatsApp",
  "Jornal",
  "Portal de Notícias",
  "Unidade de Saúde",
  "Outro",
];

const RISK_LEVELS: { value: RiskLevel; label: string }[] = [
  { value: "baixo", label: "Baixo" },
  { value: "medio", label: "Médio" },
  { value: "alto", label: "Alto" },
];

const SIGNAL_TYPES: SignalType[] = ["Abertura", "Atualização", "Encerramento"];

const CONFIDENTIALITY_LEVELS: Confidentiality[] = ["Nível 1", "Nível 2", "Nível 3"];

const STATUSES: { value: SignalStatus; label: string }[] = [
  { value: "informado", label: "Informado (Entrada)" },
  { value: "em_analise", label: "Em Análise" },
  { value: "em_monitoramento", label: "Em Monitoramento" },
  { value: "evento_confirmado", label: "Evento Confirmado" },
  { value: "descartado", label: "Descartado" },
];

const initialFormData: SignalFormData = {
  title: "",
  description: "",
  status: "informado",
  riskLevel: "baixo",
  source: "EIOS",
  signalType: "Abertura",
  confidentiality: "Nível 1",
  etiology: "",
  generalDanger: "",
  specificDanger: "",
  tags: [],
  countries: ["Brasil"],
  states: [],
  municipalities: [],
  originCountry: "Brasil",
  address: "",
  signalDate: new Date().toISOString().slice(0, 16),
  detectionDate: new Date().toISOString().slice(0, 16),
  notificationDate: "",
};

export function SignalFormModal({
  signal,
  open,
  onClose,
  onSave,
  mode,
}: SignalFormModalProps) {
  const [formData, setFormData] = useState<SignalFormData>(initialFormData);
  const [tagInput, setTagInput] = useState("");
  const [locationInput, setLocationInput] = useState({
    state: "",
    municipality: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (signal && mode === "edit") {
      // O componente exportado sincroniza o rascunho somente ao abrir/trocar o sinal.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFormData({
        title: signal.title,
        description: signal.description,
        status: signal.status,
        riskLevel: signal.riskLevel,
        source: signal.source,
        signalType: signal.signalType,
        confidentiality: signal.confidentiality,
        etiology: signal.etiology || "",
        generalDanger: signal.generalDanger || "",
        specificDanger: signal.specificDanger || "",
        tags: signal.tags,
        countries: signal.countries,
        states: signal.states,
        municipalities: signal.municipalities,
        originCountry: signal.originCountry || "",
        address: signal.address || "",
        signalDate: signal.signalDate.slice(0, 16),
        detectionDate: signal.detectionDate.slice(0, 16),
        notificationDate: signal.notificationDate?.slice(0, 16) || "",
      });
    } else {
      setFormData(initialFormData);
    }
  }, [signal, mode, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSave(formData);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const addTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData((prev) => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()],
      }));
      setTagInput("");
    }
  };

  const removeTag = (tag: string) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags.filter((t) => t !== tag),
    }));
  };

  const addState = () => {
    if (locationInput.state.trim() && !formData.states.includes(locationInput.state.trim())) {
      setFormData((prev) => ({
        ...prev,
        states: [...prev.states, locationInput.state.trim()],
      }));
      setLocationInput((prev) => ({ ...prev, state: "" }));
    }
  };

  const addMunicipality = () => {
    if (
      locationInput.municipality.trim() &&
      !formData.municipalities.includes(locationInput.municipality.trim())
    ) {
      setFormData((prev) => ({
        ...prev,
        municipalities: [...prev.municipalities, locationInput.municipality.trim()],
      }));
      setLocationInput((prev) => ({ ...prev, municipality: "" }));
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader className="pb-4 border-b">
          <DialogTitle className="text-xl">
            {mode === "create" ? "Novo Sinal" : "Editar Sinal"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
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

            <TabsContent value="info" className="mt-6 space-y-4">
              {/* Title */}
              <div className="space-y-2">
                <Label htmlFor="title">Título *</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                  placeholder="Título do sinal"
                  required
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">Descrição *</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Descrição detalhada do sinal"
                  rows={3}
                  required
                />
              </div>

              {/* Row 1: Status, Risk, Source */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(v) =>
                      setFormData((prev) => ({ ...prev, status: v as SignalStatus }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUSES.map((s) => (
                        <SelectItem key={s.value} value={s.value}>
                          {s.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Nível de Risco</Label>
                  <Select
                    value={formData.riskLevel}
                    onValueChange={(v) =>
                      setFormData((prev) => ({ ...prev, riskLevel: v as RiskLevel }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RISK_LEVELS.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          {r.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Fonte</Label>
                  <Select
                    value={formData.source}
                    onValueChange={(v) =>
                      setFormData((prev) => ({ ...prev, source: v as SignalSource }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SOURCES.map((s) => (
                        <SelectItem key={s} value={s}>
                          {s}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 2: Signal Type, Confidentiality */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Tipo de Sinal</Label>
                  <Select
                    value={formData.signalType}
                    onValueChange={(v) =>
                      setFormData((prev) => ({ ...prev, signalType: v as SignalType }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SIGNAL_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Confidencialidade</Label>
                  <Select
                    value={formData.confidentiality}
                    onValueChange={(v) =>
                      setFormData((prev) => ({ ...prev, confidentiality: v as Confidentiality }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONFIDENTIALITY_LEVELS.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 3: Etiology, General Danger, Specific Danger */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="etiology">Etiologia</Label>
                  <Input
                    id="etiology"
                    value={formData.etiology}
                    onChange={(e) => setFormData((prev) => ({ ...prev, etiology: e.target.value }))}
                    placeholder="Ex: Dengue"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="generalDanger">Perigo Geral</Label>
                  <Input
                    id="generalDanger"
                    value={formData.generalDanger}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, generalDanger: e.target.value }))
                    }
                    placeholder="Ex: Arbovirose"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="specificDanger">Perigo Específico</Label>
                  <Input
                    id="specificDanger"
                    value={formData.specificDanger}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, specificDanger: e.target.value }))
                    }
                    placeholder="Ex: Dengue tipo 2"
                  />
                </div>
              </div>

              {/* Tags */}
              <div className="space-y-2">
                <Label>Etiquetas</Label>
                <div className="flex gap-2">
                  <Input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    placeholder="Adicionar etiqueta"
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTag())}
                  />
                  <Button type="button" variant="secondary" onClick={addTag}>
                    Adicionar
                  </Button>
                </div>
                {formData.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                        {tag}
                        <button
                          type="button"
                          onClick={() => removeTag(tag)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Dates */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="signalDate">Data do Sinal *</Label>
                  <Input
                    id="signalDate"
                    type="datetime-local"
                    value={formData.signalDate}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, signalDate: e.target.value }))
                    }
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="detectionDate">Data de Detecção *</Label>
                  <Input
                    id="detectionDate"
                    type="datetime-local"
                    value={formData.detectionDate}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, detectionDate: e.target.value }))
                    }
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notificationDate">Data de Notificação</Label>
                  <Input
                    id="notificationDate"
                    type="datetime-local"
                    value={formData.notificationDate}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, notificationDate: e.target.value }))
                    }
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="location" className="mt-6 space-y-4">
              {/* Origin Country */}
              <div className="space-y-2">
                <Label htmlFor="originCountry">País de Origem</Label>
                <Input
                  id="originCountry"
                  value={formData.originCountry}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, originCountry: e.target.value }))
                  }
                  placeholder="Ex: Brasil"
                />
              </div>

              {/* States */}
              <div className="space-y-2">
                <Label>Estado(s)</Label>
                <div className="flex gap-2">
                  <Input
                    value={locationInput.state}
                    onChange={(e) =>
                      setLocationInput((prev) => ({ ...prev, state: e.target.value }))
                    }
                    placeholder="Adicionar estado"
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addState())}
                  />
                  <Button type="button" variant="secondary" onClick={addState}>
                    Adicionar
                  </Button>
                </div>
                {formData.states.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.states.map((state) => (
                      <Badge key={state} variant="secondary" className="flex items-center gap-1">
                        {state}
                        <button
                          type="button"
                          onClick={() =>
                            setFormData((prev) => ({
                              ...prev,
                              states: prev.states.filter((s) => s !== state),
                            }))
                          }
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Municipalities */}
              <div className="space-y-2">
                <Label>Município(s)</Label>
                <div className="flex gap-2">
                  <Input
                    value={locationInput.municipality}
                    onChange={(e) =>
                      setLocationInput((prev) => ({ ...prev, municipality: e.target.value }))
                    }
                    placeholder="Adicionar município"
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addMunicipality())}
                  />
                  <Button type="button" variant="secondary" onClick={addMunicipality}>
                    Adicionar
                  </Button>
                </div>
                {formData.municipalities.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.municipalities.map((mun) => (
                      <Badge key={mun} variant="secondary" className="flex items-center gap-1">
                        {mun}
                        <button
                          type="button"
                          onClick={() =>
                            setFormData((prev) => ({
                              ...prev,
                              municipalities: prev.municipalities.filter((m) => m !== mun),
                            }))
                          }
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Address */}
              <div className="space-y-2">
                <Label htmlFor="address">Endereço</Label>
                <Textarea
                  id="address"
                  value={formData.address}
                  onChange={(e) => setFormData((prev) => ({ ...prev, address: e.target.value }))}
                  placeholder="Endereço completo"
                  rows={2}
                />
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="mt-6 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {mode === "create" ? "Criar Sinal" : "Salvar Alterações"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

