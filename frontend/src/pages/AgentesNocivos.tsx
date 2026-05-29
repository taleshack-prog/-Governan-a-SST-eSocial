// ==============================================================
// SST ESOCIAL GOV — Página: Agentes Nocivos (eSocial S-2240)
// Arquivo: frontend/src/pages/AgentesNocivos.tsx
// ==============================================================

import { useState } from "react";
import { ShieldAlert, Plus, AlertTriangle, CheckCircle2, Brain } from "lucide-react";
import { useAgentesNocivos } from "../hooks/useQueries";
import { Card, SectionTitle, Spinner, EmptyState } from "../components/ui";

const TIPO_CORES: Record<string, string> = {
  fisico: "bg-blue-100 text-blue-700",
  quimico: "bg-orange-100 text-orange-700",
  biologico: "bg-green-100 text-green-700",
};

export function AgentesNocivos() {
  const { data: agentes = [], isLoading } = useAgentesNocivos();
  const [filtroRevisao, setFiltroRevisao] = useState(false);

  const lista = filtroRevisao ? agentes.filter((a: any) => a.needs_review) : agentes;

  return (
    <div>
      <SectionTitle
        title="Agentes Nocivos — eSocial S-2240"
        subtitle="Exposição ocupacional mapeada. Codificação via Tabela 24 com validação IA."
      />

      <div className="flex items-center gap-4 mb-6">
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={filtroRevisao}
            onChange={(e) => setFiltroRevisao(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Exibir apenas itens pendentes de revisão humana
        </label>

        <div className="ml-auto flex items-center gap-2 text-sm text-gray-500">
          <ShieldAlert size={16} />
          <span>{agentes.filter((a: any) => a.needs_review).length} aguardando revisão</span>
        </div>
      </div>

      <Card>
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : lista.length === 0 ? (
          <EmptyState message="Nenhum agente nocivo cadastrado ainda. Envie e valide um documento LTCAT." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Código Tabela 24</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Descrição</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Nível</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Confiança IA</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Origem</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Revisão</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((a: any) => {
                  const tipoAgente = a.codigo_tabela24?.startsWith("01") ? "fisico"
                    : a.codigo_tabela24?.startsWith("02") ? "quimico" : "biologico";
                  return (
                    <tr key={a.id} className={`border-b border-gray-50 hover:bg-gray-50 ${a.needs_review ? "bg-yellow-50" : ""}`}>
                      <td className="py-3 px-3">
                        <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${TIPO_CORES[tipoAgente]}`}>
                          {a.codigo_tabela24}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-gray-700 max-w-xs" title={a.descricao_agente}>
                        <span className="line-clamp-2">{a.descricao_agente}</span>
                      </td>
                      <td className="py-3 px-3 text-gray-500 text-xs">{a.nivel_exposicao ?? "—"}</td>
                      <td className="py-3 px-3">
                        {a.confidence_score != null ? (
                          <div className="flex items-center gap-1.5">
                            <div className="w-20 bg-gray-200 rounded-full h-1.5">
                              <div
                                className="h-1.5 rounded-full"
                                style={{
                                  width: `${(a.confidence_score * 100).toFixed(0)}%`,
                                  backgroundColor: a.confidence_score >= 0.75 ? "#16a34a"
                                    : a.confidence_score >= 0.5 ? "#d97706" : "#dc2626",
                                }}
                              />
                            </div>
                            <span className="text-xs text-gray-500">{(a.confidence_score * 100).toFixed(0)}%</span>
                          </div>
                        ) : "—"}
                      </td>
                      <td className="py-3 px-3">
                        {a.created_by_ai
                          ? <span className="flex items-center gap-1 text-xs text-purple-600"><Brain size={12} /> IA</span>
                          : <span className="text-xs text-gray-500">Manual</span>
                        }
                      </td>
                      <td className="py-3 px-3">
                        {a.needs_review
                          ? <span className="flex items-center gap-1 text-xs text-yellow-600 font-medium"><AlertTriangle size={13} /> Pendente</span>
                          : <span className="flex items-center gap-1 text-xs text-green-600"><CheckCircle2 size={13} /> OK</span>
                        }
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
