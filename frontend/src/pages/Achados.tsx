// ==============================================================
// SST ESOCIAL GOV — Página: Créditos / Achados de Folha
// Etapa 3 (v2). Regra de ouro: exibe O QUE e QUANTO; nunca o fundamento jurídico.
// ==============================================================

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";

const BRL = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const ESFERA_LABEL: Record<string, string> = {
  consultivo: "Consultivo", administrativo: "Administrativo", judicial: "Judicial",
};

const TIPO_STYLE: Record<string, { badge: string; label: string }> = {
  credito: { badge: "bg-green-50 text-green-700 border-green-200", label: "Crédito a recuperar" },
  passivo: { badge: "bg-red-50 text-red-700 border-red-200",       label: "Passivo (risco)" },
  alerta:  { badge: "bg-amber-50 text-amber-700 border-amber-200", label: "Requer análise" },
};

export function Achados() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["achados"],
    queryFn: () => apiClient.get("/achados/").then(r => r.data),
  });

  const recalcular = useMutation({
    mutationFn: () => apiClient.post("/achados/recalcular").then(r => r.data),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ["achados"] });
      setMsg(`Análise concluída: ${res.creditos} crédito(s) identificado(s).`);
    },
    onError: () => setMsg("Não foi possível recalcular agora."),
  });

  if (isLoading) return <div className="p-6 text-center text-gray-400">Carregando achados...</div>;

  const achados = data?.achados || [];
  const totalCredito = data?.total_credito || 0;
  const totalPrescreve90 = data?.total_prescreve_90dias || 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Créditos e Achados</h1>
          <p className="text-sm text-gray-500 mt-1">
            Divergências de custeio identificadas na folha — crédito a recuperar e riscos a controlar
          </p>
        </div>
        <button
          onClick={() => recalcular.mutate()}
          disabled={recalcular.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {recalcular.isPending ? "Analisando..." : "↻ Recalcular análise"}
        </button>
      </div>

      {msg && <div className="text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">{msg}</div>}

      <div className="bg-gradient-to-r from-emerald-700 to-emerald-600 text-white rounded-xl p-5">
        <p className="text-sm text-emerald-100">Crédito estimado a recuperar (últimos 5 anos)</p>
        <p className="text-3xl font-bold mt-1">{BRL(totalCredito)}</p>
        {totalPrescreve90 > 0 && (
          <div className="mt-3 bg-amber-400/20 border border-amber-300/40 rounded-lg px-3 py-2">
            <p className="text-sm font-medium text-amber-50">
              ⏳ {BRL(totalPrescreve90)} prescrevem nos próximos 90 dias
            </p>
            <p className="text-xs text-amber-100/80">
              Art. 168 do CTN — recuperação quinquenal. A cada mês, uma competência sai da janela.
            </p>
          </div>
        )}
        <p className="text-xs text-emerald-100 mt-2">
          Estimativa com base na parametrização informada. Valores confirmados na análise jurídica.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {achados.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            Nenhum achado ainda. Clique em "Recalcular análise" após cadastrar as rubricas da folha.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Achado","Tipo","Valor mensal","Retroativo (5 anos)","Prescreve até",""].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {achados.map((a: any) => {
                const s = TIPO_STYLE[a.tipo] || TIPO_STYLE.alerta;
                return (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 font-medium text-gray-900">
                      {a.descricao}
                      {a.esfera && (
                        <span className="ml-2 text-xs font-normal px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          {ESFERA_LABEL[a.esfera] || a.esfera}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <span className={`text-xs px-2 py-1 rounded border ${s.badge}`}>{s.label}</span>
                    </td>
                    <td className="px-4 py-4 text-gray-700">{BRL(a.valor_mensal)}</td>
                    <td className="px-4 py-4 font-semibold text-gray-900">{BRL(a.valor_retroativo)}</td>
                    <td className="px-4 py-4 text-xs text-amber-700">
                      {a.prescricao ? a.prescricao.data_prescricao_proxima.split("-").reverse().join("/") : "—"}
                    </td>
                    <td className="px-4 py-4 text-right">
                      <button
                        onClick={() => alert("Solicitação de análise jurídica registrada. A equipe entrará em contato.")}
                        className="text-blue-600 hover:text-blue-800 text-xs font-medium">
                        Solicitar análise →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
