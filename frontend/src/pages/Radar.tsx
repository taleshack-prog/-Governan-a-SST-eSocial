// ==============================================================
// SST ESOCIAL GOV — Página: Radar Previdenciário
// Arquivo: frontend/src/pages/Radar.tsx
// ==============================================================

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

const RISCO_COR: Record<string, string> = {
  alto:  "text-red-600 bg-red-50 border-red-200",
  medio: "text-orange-600 bg-orange-50 border-orange-200",
  baixo: "text-green-600 bg-green-50 border-green-200",
};

const ALERTA_COR: Record<string, string> = {
  critico: "border-l-4 border-red-500 bg-red-50",
  atencao: "border-l-4 border-orange-400 bg-orange-50",
  info:    "border-l-4 border-blue-400 bg-blue-50",
};

export default function Radar() {
  const { data, isLoading } = useQuery({
    queryKey: ["radar-dashboard"],
    queryFn: () => apiClient.get("/radar/dashboard/").then(r => r.data),
  });

  const { data: setores = [] } = useQuery({
    queryKey: ["radar-setores"],
    queryFn: () => apiClient.get("/radar/setores/").then(r => r.data),
  });

  if (isLoading) return (
    <div className="p-6 text-center text-gray-400">Calculando riscos...</div>
  );

  const k = data?.kpis || {};
  const f = data?.financeiro || {};

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🎯 Radar Previdenciário</h1>
          <p className="text-sm text-gray-500 mt-1">
            Visão de riscos previdenciários e exposição financeira da empresa
          </p>
        </div>
        {data?.grau_risco && (
          <div className="bg-orange-50 border border-orange-200 rounded-xl px-4 py-2 text-center">
            <p className="text-xs text-orange-600 font-medium">Grau de Risco</p>
            <p className="text-3xl font-black text-orange-600">{data.grau_risco}</p>
          </div>
        )}
      </div>

      {/* Score geral */}
      {data?.score_risco !== undefined && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-gray-700">Score de Risco Previdenciário</p>
            <span className={`text-lg font-black ${
              data.score_risco >= 70 ? "text-red-600" :
              data.score_risco >= 40 ? "text-orange-500" : "text-green-600"
            }`}>
              {data.score_risco}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${
                data.score_risco >= 70 ? "bg-red-500" :
                data.score_risco >= 40 ? "bg-orange-400" : "bg-green-500"
              }`}
              style={{ width: `${data.score_risco}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {data.score_risco >= 70 ? "🔴 Risco Alto — ação imediata necessária" :
             data.score_risco >= 40 ? "🟠 Risco Médio — monitoramento necessário" :
             "🟢 Risco Baixo — empresa em conformidade"}
          </p>
        </div>
      )}

      {/* KPIs principais */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">👥</span>
            <div>
              <p className="text-xs text-gray-500">Funcionários em Risco</p>
              <p className="text-2xl font-black text-red-600">{k.funcionarios_em_risco || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📄</span>
            <div>
              <p className="text-xs text-gray-500">Docs com Problema</p>
              <p className="text-2xl font-black text-orange-600">{k.documentos_com_problema || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🏥</span>
            <div>
              <p className="text-xs text-gray-500">Afastamentos Ativos</p>
              <p className="text-2xl font-black text-purple-600">{k.afastamentos_ativos || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">💰</span>
            <div>
              <p className="text-xs text-gray-500">Dinheiro em Risco</p>
              <p className="text-xl font-black text-red-600">
                R$ {((k.dinheiro_em_risco || 0) / 1000).toFixed(0)}k
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Painel Financeiro */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-800 mb-4">💵 Exposição Financeira</h2>
          <div className="space-y-3">
            {[
              { label: "Folha Mensal Estimada", value: f.folha_mensal, prefix: "R$" },
              { label: `Custo RAT Mensal (${f.rat_percentual}%)`, value: f.custo_rat_mensal, prefix: "R$" },
              { label: "Custo RAT Anual", value: f.custo_rat_anual, prefix: "R$" },
              { label: "Passivo Previdenciário Est.", value: f.passivo_estimado, prefix: "R$" },
              { label: "Custo Afastamentos", value: k.custo_afastamentos, prefix: "R$" },
            ].map((item) => (
              <div key={item.label} className="flex justify-between items-center py-2 border-b border-gray-50">
                <span className="text-xs text-gray-600">{item.label}</span>
                <span className="text-sm font-bold text-gray-800">
                  {item.prefix} {Number(item.value || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                </span>
              </div>
            ))}
            <div className="flex justify-between items-center py-2 bg-red-50 rounded-lg px-3 mt-2">
              <span className="text-xs font-bold text-red-700">TOTAL EM RISCO</span>
              <span className="text-base font-black text-red-700">
                R$ {Number(k.dinheiro_em_risco || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>

        {/* Alertas principais */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-800 mb-4">🚨 Alertas Principais</h2>
          {data?.alertas?.length === 0 ? (
            <div className="text-center py-6 text-gray-400">
              <p className="text-3xl mb-2">✅</p>
              <p className="text-sm">Nenhum alerta crítico</p>
            </div>
          ) : (
            <div className="space-y-3">
              {data?.alertas?.map((alerta: any, i: number) => (
                <div key={i} className={`rounded-lg p-3 ${ALERTA_COR[alerta.tipo] || "bg-gray-50"}`}>
                  <div className="flex items-start gap-2">
                    <span className="text-lg">{alerta.icone}</span>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-800">{alerta.mensagem}</p>
                      <p className="text-xs text-blue-600 mt-1 cursor-pointer hover:underline">{alerta.acao} →</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Agentes Nocivos por Setor */}
      {setores.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-800 mb-4">☢️ Setores com Agentes Nocivos</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {setores.map((setor: any, i: number) => (
              <div key={i} className={`border rounded-lg p-3 ${RISCO_COR[setor.nivel_risco]}`}>
                <div className="flex justify-between items-center mb-2">
                  <p className="text-sm font-bold">{setor.codigo}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${RISCO_COR[setor.nivel_risco]}`}>
                    {setor.nivel_risco === "alto" ? "🔴 Alto" : setor.nivel_risco === "medio" ? "🟠 Médio" : "🟢 Baixo"}
                  </span>
                </div>
                <p className="text-xs text-gray-600 mb-2">{setor.nome}</p>
                {setor.agentes.map((a: any, j: number) => (
                  <div key={j} className="text-xs text-gray-700 flex gap-2 items-center">
                    <span className="font-mono bg-white px-1 rounded border">{a.codigo_tabela24}</span>
                    <span>{a.nivel || "Qualitativo"}</span>
                    {!a.epi_eficaz && <span className="text-red-600 font-bold">EPI ineficaz</span>}
                  </div>
                ))}
                {setor.atividade_especial && (
                  <p className="text-xs font-bold text-red-700 mt-2">⚠️ Atividade Especial — Aposentadoria 25 anos</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documentos com Problema */}
      {data?.documentos_problema?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-800 mb-4">📋 Documentos que Precisam de Atenção</h2>
          <div className="space-y-2">
            {data.documentos_problema.map((doc: any) => (
              <div key={doc.id} className="flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-800">{doc.titulo}</p>
                  <p className="text-xs text-gray-500">{doc.tipo} — Status: {doc.status}</p>
                </div>
                {doc.vencido && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full font-medium">Vencido</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
