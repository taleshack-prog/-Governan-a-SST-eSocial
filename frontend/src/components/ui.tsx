// ==============================================================
// SST ESOCIAL GOV — Componentes Reutilizáveis
// Arquivo: frontend/src/components/ui.tsx
// ==============================================================

import React from "react";
import { Loader2, CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";

// ---- STATUS BADGE ----
const STATUS_CONFIG: Record<string, { label: string; classes: string }> = {
  ativo:         { label: "Ativo",         classes: "bg-green-100 text-green-800" },
  rascunho:      { label: "Rascunho",      classes: "bg-gray-100 text-gray-700" },
  vencido:       { label: "Vencido",       classes: "bg-red-100 text-red-700" },
  substituido:   { label: "Substituído",   classes: "bg-yellow-100 text-yellow-700" },
  pendente:      { label: "Pendente",      classes: "bg-blue-100 text-blue-700" },
  processando:   { label: "Processando",   classes: "bg-indigo-100 text-indigo-700" },
  concluido:     { label: "Concluído",     classes: "bg-green-100 text-green-800" },
  erro:          { label: "Erro",          classes: "bg-red-100 text-red-700" },
  enviado:       { label: "Enviado",       classes: "bg-cyan-100 text-cyan-700" },
  aceito:        { label: "Aceito",        classes: "bg-green-100 text-green-800" },
  rejeitado:     { label: "Rejeitado",     classes: "bg-red-100 text-red-700" },
  apto:          { label: "Apto",          classes: "bg-green-100 text-green-800" },
  apto_restricoes:{ label: "Apto c/ Restr.", classes: "bg-yellow-100 text-yellow-700" },
  inapto:        { label: "Inapto",        classes: "bg-red-100 text-red-700" },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, classes: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}>
      {cfg.label}
    </span>
  );
}

// ---- GRADE BADGE ----
const GRADE_CONFIG: Record<string, { classes: string; label: string }> = {
  A: { classes: "bg-green-600 text-white",  label: "A — Alta Confiança" },
  B: { classes: "bg-teal-600 text-white",   label: "B — Boa Confiança" },
  C: { classes: "bg-yellow-500 text-white", label: "C — Moderada" },
  D: { classes: "bg-orange-500 text-white", label: "D — Baixa" },
  F: { classes: "bg-red-600 text-white",    label: "F — Insuficiente" },
};

export function GradeBadge({ grade }: { grade: string }) {
  const cfg = GRADE_CONFIG[grade] ?? { classes: "bg-gray-400 text-white", label: grade };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded text-sm font-bold ${cfg.classes}`}>
      {cfg.label}
    </span>
  );
}

// ---- SPINNER ----
export function Spinner({ size = 24 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-indigo-600" />;
}

// ---- CARD ----
export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 p-6 ${className}`}>
      {children}
    </div>
  );
}

// ---- STAT CARD ----
export function StatCard({
  title, value, icon: Icon, color = "indigo", subtitle,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color?: "indigo" | "green" | "red" | "yellow" | "blue";
  subtitle?: string;
}) {
  const colorMap: Record<string, string> = {
    indigo: "bg-indigo-50 text-indigo-600",
    green:  "bg-green-50 text-green-600",
    red:    "bg-red-50 text-red-600",
    yellow: "bg-yellow-50 text-yellow-600",
    blue:   "bg-blue-50 text-blue-600",
  };
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-xl ${colorMap[color]}`}>
          <Icon size={24} />
        </div>
      </div>
    </Card>
  );
}

// ---- EMPTY STATE ----
export function EmptyState({ message = "Nenhum item encontrado." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-400">
      <Clock size={40} className="mb-3 opacity-40" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ---- ALERT ----
export function Alert({
  type = "info", message,
}: {
  type?: "info" | "success" | "warning" | "error";
  message: string;
}) {
  const configs = {
    info:    { icon: Clock,         classes: "bg-blue-50 border-blue-300 text-blue-800" },
    success: { icon: CheckCircle2,  classes: "bg-green-50 border-green-300 text-green-800" },
    warning: { icon: AlertTriangle, classes: "bg-yellow-50 border-yellow-300 text-yellow-800" },
    error:   { icon: XCircle,       classes: "bg-red-50 border-red-300 text-red-800" },
  };
  const { icon: Icon, classes } = configs[type];
  return (
    <div className={`flex items-start gap-3 border rounded-lg p-4 ${classes}`}>
      <Icon size={18} className="mt-0.5 flex-shrink-0" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ---- SECTION TITLE ----
export function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}
