"use client";

import type { Signal, SignalStatus } from "@/v0/lib/types";
import { STATUS_CONFIG } from "@/v0/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/v0/components/ui/card";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import { TrendingUp, TrendingDown, Activity, AlertCircle, CheckCircle, Clock } from "lucide-react";

interface IndicatorsViewProps {
  signals: Signal[];
}

const RISK_COLORS = {
  alto: "#dc2626",
  medio: "#f59e0b",
  baixo: "#16a34a",
};

const STATUS_COLORS: Record<SignalStatus, string> = {
  informado: "#3b82f6",
  em_analise: "#f59e0b",
  em_monitoramento: "#06b6d4",
  evento_confirmado: "#dc2626",
  descartado: "#6b7280",
};

export function IndicatorsView({ signals }: IndicatorsViewProps) {
  // Risk level distribution
  const riskData = [
    { name: "Alto", value: signals.filter((s) => s.riskLevel === "alto").length, color: RISK_COLORS.alto },
    { name: "Médio", value: signals.filter((s) => s.riskLevel === "medio").length, color: RISK_COLORS.medio },
    { name: "Baixo", value: signals.filter((s) => s.riskLevel === "baixo").length, color: RISK_COLORS.baixo },
  ];

  // Status distribution
  const statusData = Object.entries(STATUS_CONFIG).map(([status, config]) => {
    const count = signals.filter((s) => s.status === status).length;
    return {
      name: config.title.replace(" (Entrada)", "").substring(0, 15),
      fullName: config.title,
      value: count,
      color: STATUS_COLORS[status as SignalStatus] || "#6b7280",
    };
  }).filter(item => item.value > 0 || true); // Include all statuses

  // Source distribution
  const sourceData = Object.entries(
    signals.reduce((acc, signal) => {
      acc[signal.source] = (acc[signal.source] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  ).map(([name, value]) => ({ name, quantidade: value }));

  // Timeline data (signals by month)
  const timelineData = signals.reduce((acc, signal) => {
    const date = new Date(signal.signalDate);
    const monthYear = `${date.toLocaleString("pt-BR", { month: "short" })}/${date.getFullYear().toString().slice(-2)}`;
    const existing = acc.find((item) => item.month === monthYear);
    if (existing) {
      existing.total += 1;
      if (signal.riskLevel === "alto") existing.alto += 1;
      if (signal.riskLevel === "medio") existing.medio += 1;
      if (signal.riskLevel === "baixo") existing.baixo += 1;
    } else {
      acc.push({
        month: monthYear,
        total: 1,
        alto: signal.riskLevel === "alto" ? 1 : 0,
        medio: signal.riskLevel === "medio" ? 1 : 0,
        baixo: signal.riskLevel === "baixo" ? 1 : 0,
      });
    }
    return acc;
  }, [] as { month: string; total: number; alto: number; medio: number; baixo: number }[]);

  // Location data - using municipalities array from signal
  const locationData = Object.entries(
    signals.reduce((acc, signal) => {
      const location = signal.municipalities?.[0] || signal.states?.[0] || signal.countries?.[0] || "Desconhecido";
      acc[location] = (acc[location] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name, value]) => ({ name: name.substring(0, 12), sinais: value }));

  // KPIs
  const totalSignals = signals.length;
  const highRiskSignals = signals.filter((s) => s.riskLevel === "alto").length;
  const confirmedEvents = signals.filter((s) => s.status === "evento_confirmado").length;
  const pendingAnalysis = signals.filter((s) => s.status === "em_analise" || s.status === "informado").length;
  const resolvedCount = confirmedEvents + signals.filter((s) => s.status === "descartado").length;
  const avgResolutionRate = totalSignals > 0 ? ((resolvedCount / totalSignals) * 100).toFixed(1) : "0";

  // Summary table data
  const summaryStatuses: SignalStatus[] = ["informado", "em_analise", "em_monitoramento", "evento_confirmado", "descartado"];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Indicadores</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Painel estratégico de vigilância epidemiológica
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-t-4 border-t-primary">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total de Sinais</p>
                <p className="text-3xl font-bold text-foreground">{totalSignals}</p>
              </div>
              <div className="p-2 bg-primary/10 rounded-lg">
                <Activity className="h-5 w-5 text-primary" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-sm">
              <TrendingUp className="h-4 w-4 text-[#16a34a]" />
              <span className="text-[#16a34a]">+12%</span>
              <span className="text-muted-foreground">vs mês anterior</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-t-4 border-t-[#dc2626]">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Alto Risco</p>
                <p className="text-3xl font-bold text-[#dc2626]">{highRiskSignals}</p>
              </div>
              <div className="p-2 bg-[#dc2626]/10 rounded-lg">
                <AlertCircle className="h-5 w-5 text-[#dc2626]" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-sm">
              <TrendingDown className="h-4 w-4 text-[#16a34a]" />
              <span className="text-[#16a34a]">-5%</span>
              <span className="text-muted-foreground">vs mês anterior</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-t-4 border-t-[#f59e0b]">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pendentes</p>
                <p className="text-3xl font-bold text-[#f59e0b]">{pendingAnalysis}</p>
              </div>
              <div className="p-2 bg-[#f59e0b]/10 rounded-lg">
                <Clock className="h-5 w-5 text-[#f59e0b]" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-sm">
              <span className="text-muted-foreground">Aguardando análise</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-t-4 border-t-[#16a34a]">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Taxa de Resolução</p>
                <p className="text-3xl font-bold text-[#16a34a]">{avgResolutionRate}%</p>
              </div>
              <div className="p-2 bg-[#16a34a]/10 rounded-lg">
                <CheckCircle className="h-5 w-5 text-[#16a34a]" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-sm">
              <TrendingUp className="h-4 w-4 text-[#16a34a]" />
              <span className="text-[#16a34a]">+3%</span>
              <span className="text-muted-foreground">vs mês anterior</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution Pie Chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium text-foreground">
              Monitoramento de Risco
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {riskData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Status Distribution Bar Chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium text-foreground">
              Gargalos do Processo
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                  <XAxis type="number" />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    width={100}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{ 
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    formatter={(value, name, props) => [value, props.payload.fullName]}
                  />
                  <Bar dataKey="value" name="Quantidade">
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline Chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium text-foreground">
              Evolução Temporal dos Sinais
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timelineData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <Tooltip
                    contentStyle={{ 
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="alto"
                    name="Alto"
                    stackId="1"
                    stroke={RISK_COLORS.alto}
                    fill={RISK_COLORS.alto}
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="medio"
                    name="Médio"
                    stackId="1"
                    stroke={RISK_COLORS.medio}
                    fill={RISK_COLORS.medio}
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="baixo"
                    name="Baixo"
                    stackId="1"
                    stroke={RISK_COLORS.baixo}
                    fill={RISK_COLORS.baixo}
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Source Distribution */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium text-foreground">
              Sinais por Fonte de Informação
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sourceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis />
                  <Tooltip
                    contentStyle={{ 
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="quantidade" name="Sinais" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Locations */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium text-foreground">
              Principais Localidades
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={locationData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                  <XAxis type="number" />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    width={90}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{ 
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="sinais" name="Sinais" fill="#06b6d4" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Summary Table */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium text-foreground">
              Resumo por Status e Risco
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-2 font-medium text-muted-foreground">Status</th>
                    <th className="text-center py-2 px-2 font-medium text-[#dc2626]">Alto</th>
                    <th className="text-center py-2 px-2 font-medium text-[#f59e0b]">Médio</th>
                    <th className="text-center py-2 px-2 font-medium text-[#16a34a]">Baixo</th>
                    <th className="text-center py-2 px-2 font-medium text-foreground">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {summaryStatuses.map((status) => {
                    const statusSignals = signals.filter((s) => s.status === status);
                    const alto = statusSignals.filter((s) => s.riskLevel === "alto").length;
                    const medio = statusSignals.filter((s) => s.riskLevel === "medio").length;
                    const baixo = statusSignals.filter((s) => s.riskLevel === "baixo").length;
                    return (
                      <tr key={status} className="border-b border-border/50 hover:bg-muted/30">
                        <td className="py-2 px-2 text-foreground">{STATUS_CONFIG[status].title.replace(" (Entrada)", "")}</td>
                        <td className="text-center py-2 px-2 text-foreground">{alto}</td>
                        <td className="text-center py-2 px-2 text-foreground">{medio}</td>
                        <td className="text-center py-2 px-2 text-foreground">{baixo}</td>
                        <td className="text-center py-2 px-2 font-medium text-foreground">{statusSignals.length}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

