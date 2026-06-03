// ==============================================================
// RADAR PREVIDENCIÁRIO — Afastamentos RH
// Arquivo: frontend/src/pages/AfastamentosRH.tsx
// ==============================================================
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Calendar, FileText, Clock } from "lucide-react";
import { apiClient } from "../api/client";
import { SectionTitle, Spinner, StatusBadge } from "../components/ui";

const FILTROS = ["Todos", "Novos", "Pendentes", "Retorno"];

export default function AfastamentosRH() {
  const [filtro, setFiltro] = useState("Todos");
  const qc = useQueryClient();

  const { data: afastamentos = [], isLoading } = useQuery({
    queryKey: ["afastamentos-rh"],
    queryFn: () => apiClient.get("/afastamentos/").then(r => r.data),
    refetchInterval: 30000,
  });

  const hoje = new Date();

  const novosHoje = afastamentos.filter((a: any) => {
    const d = new Date(a.data_inicio);
    return d.toDateString() === hoje.toDateString();
  }).length;

  const pendentes = afastamentos.filter((a: any) =>
    ["recebido", "em_analise"].includes(a.status)
  ).length;

  const retornoProximo = afastamentos.filter((a: any) => {
    if (!a.data_prevista_retorno) return false;
    const diff = (new Date(a.data_prevista_retorno).getTime() - hoje.getTime()) / (1000*60*60*24);
    return diff >= 0 && diff <= 3;
  }).length;

  const criticos = afastamentos.filter((a: any) =>
    ["limbo", "alta_inss"].includes(a.status)
  ).length;

  const filtrados = afastamentos.filter((a: any) => {
    if (filtro === "Todos") return true;
    if (filtro === "Novos") return new Date(a.data_inicio).toDateString() === hoje.toDateString();
    if (filtro === "Pendentes") return ["recebido", "em_analise"].includes(a.status);
    if (filtro === "Retorno") {
      if (!a.data_prevista_retorno) return false;
      const diff = (new Date(a.data_prevista_retorno).getTime() - hoje.getTime()) / (1000*60*60*24);
      return diff >= 0 && diff <= 7;
    }
    return true;
  });

  const getIconeStatus = (a: any) => {
    if (a.status === "limbo" || a.status === "alta_inss") return <AlertTriangle size={14} className="text-red-500" />;
    if (a.status === "retorno_proximo") return <Calendar size={14} className="text-blue-500" />;
    if (a.status === "em_analise") return <Clock size={14} className="text-yellow-500" />;
    return <FileText size={14} className="text-gray-400" />;
  };

  const getDescricao = (a: any) => {
    if (a.num_atestados > 0) return `Atestado enviado`;
    if (a.data_prevista_retorno) {
      const diff = Math.ceil((new Date(a.data_prevista_retorno).getTime() - hoje.getTime()) / (1000*60*60*24));
      if (diff > 0) return `Retorno em ${diff} dia(s)`;
      return `Retorno previsto`;
    }
    return `Documento incompleto`;
  };

  const getDataRelativa = (data: string) => {
    const d = new Date(data);
    const diff = Math.floor((hoje.getTime() - d.getTime()) / (1000*60*60*24));
    if (diff === 0) return "Hoje";
    if (diff === 1) return "Ontem";
    return `${diff} dias atrás`;
  };

  if (isLoading) return <div className="flex justify-center items-center h-64"><Spinner size={32} /></div>;

  return (
    <div className="space-y-6">
      <SectionTitle title="Afastamentos RH" subtitle="Fila do RH e casos em tratamento" />

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: "Novos hoje", value: novosHoje, color: "text-teal-600", bg: "bg-teal-50" },
          { label: "Pendentes", value: pendentes, color: "text-orange-500", bg: "bg-orange-50" },
          { label: "Retorno próximo", value: retornoProximo, color: "text-blue-600", bg: "bg-blue-50" },
          { label: "Críticos", value: criticos, color: "text-red-500", bg: "bg-red-50" },
        ].map((k, i) => (
          <div key={i} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <p className="text-sm text-gray-500 mb-1">{k.label}</p>
            <p className={`text-3xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap">
        {FILTROS.map(f => (
          <button key={f} onClick={() => setFiltro(f)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              filtro === f
                ? "bg-[#0f2744] text-white"
                : "bg-white border border-gray-200 text-gray-600 hover:border-gray-400"
            }`}>
            {f}
          </button>
        ))}
      </div>

      {/* Lista */}
      <div className="space-y-3">
        {filtrados.length === 0 ? (
          <div className="bg-white rounded-xl p-8 text-center text-gray-400 text-sm">
            Nenhum afastamento encontrado.
          </div>
        ) : (
          filtrados.map((a: any) => (
            <div key={a.id} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-teal-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                    {a.trabalhador_nome?.split(" ").map((n: string) => n[0]).slice(0,2).join("")}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">{a.trabalhador_nome}</p>
                    <p className="text-xs text-gray-500">{a.trabalhador_setor || a.cid || "—"}</p>
                    <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
                      {getIconeStatus(a)}
                      <span>{getDescricao(a)}</span>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <StatusBadge status={a.status} />
                  <span className="text-xs text-gray-400">{getDataRelativa(a.data_inicio)}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
