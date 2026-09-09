// ==============================================================
// SST ESOCIAL GOV — Página: Diagnóstico (tela inicial dos 4 blocos)
// Alteração 2 (v2): abertura do sistema. Regra de ouro: exibe O QUE e QUANTO;
// NUNCA o fundamento jurídico.
// ==============================================================

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

const BRL = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const SEMAFORO: Record<string, { dot: string; badge: string; label: string }> = {
  verde:    { dot: "bg-green-500",  badge: "bg-green-50 text-green-700 border-green-200",   label: "Conferido" },
  amarelo:  { dot: "bg-amber-400",  badge: "bg-amber-50 text-amber-700 border-amber-200",   label: "Pendência de informação" },
  vermelho: { dot: "bg-red-500",    badge: "bg-red-50 text-red-700 border-red-200",         label: "Divergência identificada" },
};

interface AchadoModalProps { bloco: any; onFechar: () => void; }

function AchadoModal({ bloco, onFechar }: AchadoModalProps) {
  const impacto = bloco.impacto_anual_estimado;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
          <h2 className="text-lg font-bold text-gray-900">{bloco.bloco}</h2>
        </div>
        <p className="text-sm text-gray-500 mb-4">Divergência identificada no enquadramento</p>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-gray-600">Valor pago / mês</span><span className="font-medium">{BRL(bloco.valor_pago_mensal)}</span></div>
          <div className="flex justify-between"><span className="text-gray-600">Valor esperado / mês</span><span className="font-medium">{BRL(bloco.valor_esperado_mensal)}</span></div>
          <div className="flex justify-between border-t pt-2 mt-2">
            <span className="text-gray-800 font-medium">Impacto anual estimado</span>
            <span className="font-bold text-red-600">{BRL(impacto)}</span>
          </div>
          {bloco.natureza && (
            <p className="text-xs text-gray-500 pt-1">
              {bloco.natureza === "credito"
                ? "Você paga a mais do que o enquadramento indica — valor potencialmente recuperável."
                : bloco.natureza === "passivo"
                ? "Você paga a menos do que o enquadramento indica — risco de passivo."
                : ""}
            </p>
          )}
        </div>

        <div className="mt-5 flex gap-3">
          <button onClick={onFechar} className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50">Fechar</button>
          <button
            onClick={() => alert("Solicitação de análise jurídica registrada. A equipe jurídica entrará em contato.")}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700">
            Solicitar análise jurídica
          </button>
        </div>
      </div>
    </div>
  );
}

export function Diagnostico() {
  const [achado, setAchado] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["diagnostico-blocos"],
    queryFn: () => apiClient.get("/diagnostico/blocos").then(r => r.data),
  });

  const { data: achadosData } = useQuery({
    queryKey: ["achados"],
    queryFn: () => apiClient.get("/achados/").then(r => r.data),
  });

  if (isLoading) return <div className="p-6 text-center text-gray-400">Calculando diagnóstico...</div>;

  const blocos = data?.blocos || [];
  const resumo = data?.resumo || {};
  const totalPago = blocos.reduce((s: number, b: any) => s + (b.valor_pago_mensal || 0), 0);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Diagnóstico de Custeio</h1>
        <p className="text-sm text-gray-500 mt-1">
          Visão do custeio previdenciário da empresa — o que você paga vs. o que o enquadramento correto indica
        </p>
      </div>

      <div className="bg-gradient-to-r from-slate-800 to-slate-700 text-white rounded-xl p-5">
        <p className="text-sm text-slate-300">Custeio apurado nos blocos calculados</p>
        <p className="text-3xl font-bold mt-1">{BRL(totalPago)}<span className="text-base font-normal text-slate-300"> / mês</span></p>
        <p className="text-sm mt-2">
          {resumo.blocos_divergentes > 0
            ? <span className="text-red-300 font-medium">{resumo.blocos_divergentes} bloco(s) com divergência</span>
            : <span className="text-green-300">Nenhuma divergência nos blocos calculados</span>}
          {resumo.blocos_pendentes > 0 && <span className="text-amber-300"> · {resumo.blocos_pendentes} pendente(s) de informação</span>}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Bloco","Valor pago / mês","Valor esperado / mês","Situação",""].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {blocos.map((b: any) => {
              const s = SEMAFORO[b.semaforo] || SEMAFORO.amarelo;
              const clicavel = b.semaforo === "vermelho";
              return (
                <tr key={b.bloco} className={clicavel ? "hover:bg-red-50 cursor-pointer" : ""}
                    onClick={() => clicavel && setAchado(b)}>
                  <td className="px-4 py-4 font-medium text-gray-900 flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${s.dot}`} />{b.bloco}
                  </td>
                  <td className="px-4 py-4 text-gray-700">{BRL(b.valor_pago_mensal)}</td>
                  <td className="px-4 py-4 text-gray-700">{BRL(b.valor_esperado_mensal)}</td>
                  <td className="px-4 py-4">
                    <span className={`text-xs px-2 py-1 rounded border ${s.badge}`}>{s.label}</span>
                  </td>
                  <td className="px-4 py-4 text-right">
                    {clicavel && <span className="text-red-600 text-xs font-medium">Ver achado →</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {(achadosData?.total_credito || 0) > 0 && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 flex items-center justify-between">
          <div>
            <p className="text-sm text-emerald-700">Créditos de folha identificados (recuperação retroativa)</p>
            <p className="text-2xl font-bold text-emerald-800 mt-1">{BRL(achadosData.total_credito)}</p>
          </div>
          <a href="/achados" className="text-emerald-700 font-medium text-sm hover:text-emerald-900">Ver detalhes →</a>
        </div>
      )}

      {achado && <AchadoModal bloco={achado} onFechar={() => setAchado(null)} />}
    </div>
  );
}
