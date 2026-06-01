// ==============================================================
// SST ESOCIAL GOV — Página: Dashboard
// Arquivo: frontend/src/pages/Dashboard.tsx
// ==============================================================

import {
  FileText, Users, ShieldAlert, Brain,
  AlertTriangle, CheckCircle2, Clock, Stethoscope,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import { useDocumentos, useTrabalhadores, useAgentesNocivos, useValidacoes } from "../hooks/useQueries";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { StatCard, Card, SectionTitle, Spinner, GradeBadge, StatusBadge } from "../components/ui";
import { useAuthStore } from "../store/authStore";

const GRADE_COLORS: Record<string, string> = {
  A: "#16a34a", B: "#0d9488", C: "#d97706", D: "#ea580c", F: "#dc2626",
};

export function Dashboard() {
  const { data: alertas = [] } = useQuery({
    queryKey: ["alertas"],
    queryFn: () => apiClient.get("/alertas/").then(r => r.data),
    refetchInterval: 60000, // atualiza a cada 1 minuto
  });
  const { user } = useAuthStore();
  const { data: documentos = [], isLoading: loadDocs } = useDocumentos();
  const { data: trabalhadores = [], isLoading: loadTrab } = useTrabalhadores();
  const { data: agentes = [], isLoading: loadAg } = useAgentesNocivos();
  const { data: validacoes = [], isLoading: loadVal } = useValidacoes();

  const isLoading = loadDocs || loadTrab || loadAg || loadVal;

  // KPIs calculados
  const docsAtivos = documentos.filter((d: any) => d.status === "ativo").length;
  const docsVencidos = documentos.filter((d: any) => d.status === "vencido").length;
  const agentesRevisao = agentes.filter((a: any) => a.needs_review).length;
  const valConcluidas = validacoes.filter((v: any) => v.status === "concluido").length;

  // Dados para gráficos
  const docsPorTipo = ["LTCAT", "PGR", "PCMSO", "ASO", "CAT", "AET"].map((tipo) => ({
    tipo,
    quantidade: documentos.filter((d: any) => d.tipo === tipo).length,
  }));

  const gradeContagem = validacoes.reduce((acc: Record<string, number>, v: any) => {
    const g = v.grade_label ?? "F";
    acc[g] = (acc[g] ?? 0) + 1;
    return acc;
  }, {});
  const gradePieData = Object.entries(gradeContagem).map(([name, value]) => ({ name, value }));

  const alertasCriticos = alertas.filter((a: any) => a.prioridade === "critica" || a.prioridade === "alta");

  if (isLoading) {
  return (
      <div className="flex items-center justify-center h-64">
        <Spinner size={32} />
      </div>
    );
  }

  return (
    <div>
      <SectionTitle
        title={`Olá, ${user?.nome?.split(" ")[0] ?? "usuário"} 👋`}
        subtitle="Visão geral da conformidade SST/eSocial da empresa"
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        <StatCard title="Documentos Ativos"    value={docsAtivos}   icon={FileText}    color="indigo" subtitle={`${docsVencidos} vencidos`} />
        <StatCard title="Trabalhadores"        value={trabalhadores.length} icon={Users} color="blue" />
        <StatCard title="Agentes p/ Revisão"   value={agentesRevisao} icon={ShieldAlert} color="yellow" subtitle="Aguardando validação humana" />
        <StatCard title="Validações IA"        value={valConcluidas} icon={Brain}        color="green" subtitle={`de ${validacoes.length} total`} />
      </div>

      {/* Alertas */}
      {(docsVencidos > 0 || agentesRevisao > 0) && (
        <div className="mb-8 space-y-3">
          {docsVencidos > 0 && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
              <AlertTriangle size={18} className="text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700">
                <strong>{docsVencidos} documento(s) vencidos</strong> — atualize para manter conformidade com a NR-01 e eSocial S-2240.
              </p>
            </div>
          )}
          {agentesRevisao > 0 && (
            <div className="flex items-center gap-3 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3">
              <Clock size={18} className="text-yellow-600 flex-shrink-0" />
              <p className="text-sm text-yellow-700">
                <strong>{agentesRevisao} agente(s) nocivos</strong> aguardando revisão humana após validação IA.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Alertas Automáticos */}
      {alertasCriticos.length > 0 && (
        <div className="bg-white rounded-xl border border-red-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">🚨</span>
            <h3 className="text-sm font-bold text-gray-800">Alertas Previdenciários</h3>
            <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded-full">{alertasCriticos.length}</span>
          </div>
          <div className="space-y-2">
            {alertasCriticos.map((a: any) => (
              <div key={a.id} className={`rounded-lg p-3 border-l-4 ${a.cor === "red" ? "bg-red-50 border-red-500" : "bg-orange-50 border-orange-400"}`}>
                <p className="text-xs font-medium text-gray-800">{a.mensagem}</p>
                <p className="text-xs text-gray-400 mt-1">{new Date(a.created_at).toLocaleString("pt-BR")}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Gráficos */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
        {/* Documentos por tipo */}
        <Card className="xl:col-span-2">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Documentos por Tipo</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={docsPorTipo} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="tipo" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="quantidade" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Grade das validações IA */}
        <Card>
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Grade das Validações IA</h3>
          {gradePieData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-gray-400">
              <Brain size={32} className="opacity-30 mb-2" />
              <p className="text-xs">Nenhuma validação ainda</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={gradePieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70}>
                  {gradePieData.map((entry) => (
                    <Cell key={entry.name} fill={GRADE_COLORS[entry.name] ?? "#9ca3af"} />
                  ))}
                </Pie>
                <Legend formatter={(val) => `Grade ${val}`} />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* Últimas validações */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Últimas Validações IA</h3>
        {validacoes.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">Nenhuma validação encontrada.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Tipo</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Status</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Grade</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Confiança</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Revisão</th>
                </tr>
              </thead>
              <tbody>
                {validacoes.slice(0, 8).map((v: any) => (
                  <tr key={v.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2.5 px-3 font-medium text-gray-700">{v.tipo_validacao}</td>
                    <td className="py-2.5 px-3"><StatusBadge status={v.status} /></td>
                    <td className="py-2.5 px-3">
                      {v.grade_label ? <GradeBadge grade={v.grade_label} /> : "—"}
                    </td>
                    <td className="py-2.5 px-3 text-gray-600">
                      {v.confidence_score != null ? `${(v.confidence_score * 100).toFixed(0)}%` : "—"}
                    </td>
                    <td className="py-2.5 px-3">
                      {v.needs_human_review
                        ? <span className="text-yellow-600 flex items-center gap-1"><AlertTriangle size={13} /> Sim</span>
                        : <span className="text-green-600 flex items-center gap-1"><CheckCircle2 size={13} /> Não</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
