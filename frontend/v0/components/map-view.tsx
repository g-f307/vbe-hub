"use client";

import { useEffect, useRef, useState } from "react";
import type { Signal } from "@/v0/lib/types";
import { Card, CardContent } from "@/v0/components/ui/card";
import { MapPin, AlertTriangle, Info } from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface MapViewProps {
  signals: Signal[];
  onSignalClick: (signal: Signal) => void;
}

// Coordenadas aproximadas para localidades
const locationCoordinates: Record<string, [number, number]> = {
  "Manaus": [-3.1190, -60.0217],
  "Alvorada": [-3.0833, -60.0333],
  "Centro": [-3.1300, -60.0230],
  "Jorge Teixeira": [-3.0500, -59.9400],
  "Cidade Nova": [-3.0200, -59.9700],
  "Puraquequara": [-3.0300, -59.8900],
  "Flores": [-3.0800, -60.0100],
  "Zona Rural": [-3.2000, -60.1000],
  "São Paulo": [-23.5505, -46.6333],
  "Rio de Janeiro": [-22.9068, -43.1729],
  "Brasília": [-15.7801, -47.9292],
  "Amazonas": [-3.4168, -65.8561],
  "Brasil": [-14.2350, -51.9253],
};

const getRiskColor = (risk: string) => {
  switch (risk) {
    case "alto":
      return "#dc2626";
    case "medio":
      return "#f59e0b";
    case "baixo":
      return "#16a34a";
    default:
      return "#6b7280";
  }
};

const getRiskLabel = (risk: string) => {
  switch (risk) {
    case "alto":
      return "Alto";
    case "medio":
      return "Médio";
    case "baixo":
      return "Baixo";
    default:
      return risk;
  }
};

// Get location from signal using the correct structure
const getSignalLocation = (signal: Signal): string => {
  if (signal.municipalities && signal.municipalities.length > 0) {
    return signal.municipalities[0];
  }
  if (signal.states && signal.states.length > 0) {
    return signal.states[0];
  }
  if (signal.countries && signal.countries.length > 0) {
    return signal.countries[0];
  }
  return "Desconhecido";
};

// Extract location from address field
const getLocationFromAddress = (signal: Signal): string | null => {
  if (signal.address) {
    // Try to extract neighborhood/district from address
    const parts = signal.address.split(",");
    if (parts.length > 0) {
      const location = parts[0].trim();
      if (locationCoordinates[location]) {
        return location;
      }
      // Try the second part
      if (parts.length > 1) {
        const location2 = parts[1].trim();
        if (locationCoordinates[location2]) {
          return location2;
        }
      }
    }
  }
  return null;
};

export function MapView({ signals, onSignalClick }: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !mapRef.current) return;

    const initMap = async () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
      }

      const map = L.map(mapRef.current!, {
        center: [-3.1190, -60.0217],
        zoom: 11,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);

      // Add markers for each signal
      signals.forEach((signal) => {
        // Try to get location from address first, then fall back to municipality
        let locationKey = getLocationFromAddress(signal);
        if (!locationKey) {
          locationKey = getSignalLocation(signal);
        }
        
        const coords = locationCoordinates[locationKey];
        
        if (coords) {
          // Add some randomness to prevent markers from stacking
          const lat = coords[0] + (Math.random() - 0.5) * 0.03;
          const lng = coords[1] + (Math.random() - 0.5) * 0.03;
          
          const color = getRiskColor(signal.riskLevel);
          
          const icon = L.divIcon({
            className: "custom-marker",
            html: `
              <div style="
                background-color: ${color};
                width: 24px;
                height: 24px;
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
              "></div>
            `,
            iconSize: [24, 24],
            iconAnchor: [12, 24],
          });

          const marker = L.marker([lat, lng], { icon })
            .addTo(map)
            .on("click", () => {
              onSignalClick(signal);
            });

          const displayLocation = signal.address || `${signal.municipalities?.[0] || ""}, ${signal.states?.[0] || ""}`;

          marker.bindTooltip(`
            <strong>${signal.title}</strong><br/>
            <span style="color: ${color}">Risco: ${getRiskLabel(signal.riskLevel)}</span><br/>
            ${displayLocation}
          `, {
            direction: "top",
            offset: [0, -20],
          });
        }
      });

      mapInstanceRef.current = map;
      setIsMapReady(true);
    };

    initMap();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [signals, onSignalClick]);

  // Calculate statistics
  const stats = {
    total: signals.length,
    alto: signals.filter((s) => s.riskLevel === "alto").length,
    medio: signals.filter((s) => s.riskLevel === "medio").length,
    baixo: signals.filter((s) => s.riskLevel === "baixo").length,
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Visão Geoespacial</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Distribuição geográfica dos sinais de vigilância
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-primary">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-primary" />
              <div>
                <p className="text-sm text-muted-foreground">Total de Sinais</p>
                <p className="text-2xl font-bold text-foreground">{stats.total}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-[#dc2626]">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-[#dc2626]" />
              <div>
                <p className="text-sm text-muted-foreground">Risco Alto</p>
                <p className="text-2xl font-bold text-[#dc2626]">{stats.alto}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-[#f59e0b]">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Info className="h-5 w-5 text-[#f59e0b]" />
              <div>
                <p className="text-sm text-muted-foreground">Risco Médio</p>
                <p className="text-2xl font-bold text-[#f59e0b]">{stats.medio}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-[#16a34a]">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-[#16a34a]" />
              <div>
                <p className="text-sm text-muted-foreground">Risco Baixo</p>
                <p className="text-2xl font-bold text-[#16a34a]">{stats.baixo}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Map container */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div
            ref={mapRef}
            className="h-[500px] md:h-[600px] w-full"
            style={{ minHeight: "400px" }}
          />
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-6">
            <span className="text-sm font-medium text-muted-foreground">Legenda:</span>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-[#dc2626]" />
              <span className="text-sm text-foreground">Risco Alto</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-[#f59e0b]" />
              <span className="text-sm text-foreground">Risco Médio</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-[#16a34a]" />
              <span className="text-sm text-foreground">Risco Baixo</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

