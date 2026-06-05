import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { SectionTitle, Spinner } from "../components/ui";
import { AlertTriangle, CheckCircle, XCircle, ClipboardCheck } from "lucide-react";

const GRAVIDADE: Record<string, { color: string; bg: string; border: string }> = {
  alta:  { color: "text-red-700",   bg: "bg-red-50",   border: "border-red-200" },
  media: { color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  baixa: { color: "text-green-700", bg: "bg-green-50", border: "border-green-200" },
};

export default function Inconsistencias() {
  const { data, isLoading } = useQuery({
    queryKey: ["inconsistencias"],
    queryFn: () => apiClient.get("/inconsistencias/verificar").then(r => r.data),
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="flex justify-center items-center h-64"><Spinner size={32} /></div>;

  const { inconsistencias = [], checklist = [], total_inconsistencias, criticas, score_checklist, pronto_para_esocial } = data || {};

  return (
    <div className="space-y-6">
      <SectionTitle title="Motor de Inconsistências" subtitle="Checklist pré-eSocial e erros invisíveis detectados" />

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Total de inconsistências</p>
          <p className={`text-3xl font-bold ${total_inconsistencias > 0 ? "text-red-600" : "text-green-600"}`}>{total_inconsistencias}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Críticas</p>
          <p className={`text-3xl font-bold ${criticas > 0 ? "text-red-600" : "text-green-600"}`}>{criticas}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Score pré-eSocial</p>
          <p className={`text-3xl font-bold ${score_checklist >= 80 ? "text-green-600" : score_checklist >= 50 ? "text-amber-600" : "text-red-600"}`}>{score_checklist}%</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Pronto para eSocial</p>
          <div className="flex items-center gap-2 mt-1">
            {pronto_para_esocial
              ? <CheckCircle size={28} className="text-green-500" />
              : <XCircle size={28} className="text-red-500" />}
            <span className={`text-sm font-bold ${pronto_para_esocial ? "text-green-600" : "text-red-600"}`}>
              {pronto_para_esocial ? "Sim" : "Não"}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Checklist pré-eSocial */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[#0f2744] rounded-lg flex items-center justify-center">
              <ClipboardCheck size={16} color="white" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">Checklist pré-eSocial</p>
              <p className="text-xs text-gray-400">Requisitos antes do envio</p>
            </div>
          </div>
          <div className="space-y-2.5">
            {checklist.map((c: any, i: number) => (
              <div key={i} className={`flex items-center justify-between p-3 rounded-xl border ${c.ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">{c.icone}</span>
                  <div>
                    <p className={`text-sm font-medium ${c.ok ? "text-green-800" : "text-red-800"}`}>{c.item}</p>
                    {!c.ok && c.pendente > 0 && (
                      <p className="text-xs text-red-600">{c.pendente} pendente(s)</p>
                    )}
                  </div>
                </div>
                {c.ok
                  ? <CheckCircle size={18} className="text-green-500 flex-shrink-0" />
                  : <XCircle size={18} className="text-red-500 flex-shrink-0" />}
              </div>
            ))}
          </div>
        </div>

        {/* Inconsistências detectadas */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <AlertTriangle size={16} color="white" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">Erros invisíveis detectados</p>
              <p className="text-xs text-gray-400">Problemas que causam falha no eSocial</p>
            </div>
          </div>

          {inconsistencias.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-10">
              <CheckCircle size={40} className="text-green-400" />
              <p className="text-gray-500 text-sm text-center">Nenhuma inconsistência encontrada!</p>
            </div>
          ) : (
            <div className="space-y-2.5 max-h-96 overflow-y-auto">
              {inconsistencias.map((inc: any, i: number) => {
                const cfg = GRAVIDADE[inc.gravidade] || GRAVIDADE.baixa;
                return (
                  <div key={i} className={`p-3 rounded-xl border ${cfg.bg} ${cfg.border}`}>
                    <div className="flex items-start gap-2.5">
                      <span className="text-lg flex-shrink-0">{inc.icone}</span>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-semibold ${cfg.color}`}>{inc.titulo}</p>
                        <p className="text-xs text-gray-600 mt-0.5">{inc.detalhe}</p>
                        <p className="text-xs font-medium text-[#0f2744] mt-1">→ {inc.acao}</p>
                      </div>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full border flex-shrink-0 ${cfg.color} ${cfg.bg} ${cfg.border}`}>
                        {inc.gravidade}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
