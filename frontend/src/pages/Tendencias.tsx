import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { SectionTitle, Spinner } from "../components/ui";
import { TrendingUp, TrendingDown, Minus, Trophy, Building2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const CRIT: Record<string, { color: string; bg: string; border: string }> = {
  alta:  { color: "text-red-700",   bg: "bg-red-50",   border: "border-red-200" },
  media: { color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  baixa: { color: "text-green-700", bg: "bg-green-50", border: "border-green-200" },
};

export default function Tendencias() {
  const { data: previsao, isLoading: l1 } = useQuery({
    queryKey: ["tendencias-previsao"],
    queryFn: () => apiClient.get("/tendencias/previsao-custo").then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: ranking, isLoading: l2 } = useQuery({
    queryKey: ["tendencias-ranking"],
    queryFn: () => apiClient.get("/tendencias/ranking-casos").then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: setorial, isLoading: l3 } = useQuery({
    queryKey: ["tendencias-setorial"],
    queryFn: () => apiClient.get("/tendencias/impacto-setorial").then(r => r.data),
    refetchInterval: 60000,
  });

  if (l1 || l2 || l3) return <div className="flex justify-center items-center h-64"><Spinner size={32} /></div>;

  const TrendIcon = previsao?.tendencia_dir === "subindo" ? TrendingUp :
                    previsao?.tendencia_dir === "caindo" ? TrendingDown : Minus;
  const trendColor = previsao?.tendencia_dir === "subindo" ? "text-red-500" :
                     previsao?.tendencia_dir === "caindo" ? "text-green-500" : "text-gray-400";

  return (
    <div className="space-y-6">
      <SectionTitle title="Tendências e Ranking" subtitle="Previsão de custo, casos críticos e impacto por setor" />

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Tendência</p>
          <div className="flex items-center gap-2">
            <TrendIcon size={24} className={trendColor} />
            <span className={`text-lg font-bold ${trendColor}`}>
              {previsao?.tendencia_pct > 0 ? "+" : ""}{previsao?.tendencia_pct}%
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">{previsao?.tendencia_dir}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Previsão próximo mês</p>
          <p className="text-2xl font-bold text-orange-600">
            R$ {previsao?.projecao_prox_mes?.toLocaleString("pt-BR")}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Custo acumulado total</p>
          <p className="text-2xl font-bold text-red-600">
            R$ {ranking?.total_custo_acumulado?.toLocaleString("pt-BR")}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Setor mais crítico</p>
          <p className="text-sm font-bold text-[#0f2744] leading-tight mt-1">
            {setorial?.setor_mais_critico?.split(" - ")[0] || "—"}
          </p>
        </div>
      </div>

      {/* Gráfico de tendência */}
      {previsao?.historico?.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <p className="font-bold text-gray-900 text-sm mb-4">Evolução de custos por mês</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={previsao.historico}>
              <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `R$${(v/1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: any) => [`R$ ${Number(v).toLocaleString("pt-BR")}`, "Custo"]} />
              <Bar dataKey="custo_total" radius={[6, 6, 0, 0]}>
                {previsao.historico.map((h: any, i: number) => (
                  <Cell key={i} fill={h.projecao ? "#94a3b8" : "#0f2744"} fillOpacity={h.projecao ? 0.5 : 1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-400 mt-2 text-center">Barras cinzas = projeção</p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Ranking de casos */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <Trophy size={16} color="white" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">Ranking de impacto</p>
              <p className="text-xs text-gray-400">Casos que mais drenam custo e operação</p>
            </div>
          </div>
          <div className="space-y-3">
            {ranking?.ranking?.map((r: any) => (
              <div key={r.posicao} className="flex items-start gap-3 p-3 rounded-xl bg-gray-50 border border-gray-100">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${
                  r.posicao === 1 ? "bg-yellow-400 text-yellow-900" :
                  r.posicao === 2 ? "bg-gray-300 text-gray-700" :
                  r.posicao === 3 ? "bg-orange-300 text-orange-800" :
                  "bg-gray-100 text-gray-500"
                }`}>
                  {r.posicao}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-gray-900">{r.trabalhador}</p>
                    <span className="text-xs font-bold text-red-600 flex-shrink-0">
                      R$ {r.custo_acumulado?.toLocaleString("pt-BR")}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">{r.setor} · CID: {r.cid} · {r.dias_afastado} dias</p>
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {r.fatores.map((f: string, i: number) => (
                      <span key={i} className="text-xs bg-red-50 text-red-600 border border-red-200 px-2 py-0.5 rounded-full">{f}</span>
                    ))}
                  </div>
                  {/* Score bar */}
                  <div className="mt-1.5 flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-red-500 h-1.5 rounded-full" style={{ width: `${r.score_impacto}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 flex-shrink-0">score {r.score_impacto}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Impacto setorial */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[#0f2744] rounded-lg flex items-center justify-center">
              <Building2 size={16} color="white" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">Impacto operacional por setor</p>
              <p className="text-xs text-gray-400">Capacidade reduzida por afastamentos</p>
            </div>
          </div>
          <div className="space-y-3">
            {setorial?.setores?.map((s: any, i: number) => {
              const cfg = CRIT[s.criticidade] || CRIT.baixa;
              return (
                <div key={i} className={`p-3 rounded-xl border ${cfg.bg} ${cfg.border}`}>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <p className={`text-sm font-semibold ${cfg.color}`}>{s.setor}</p>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${cfg.color} ${cfg.bg} ${cfg.border}`}>
                      {s.criticidade}
                    </span>
                  </div>
                  <div className="flex gap-4 text-xs text-gray-600 mb-2">
                    <span>{s.afastados}/{s.total_trabalhadores} afastados</span>
                    <span>R$ {s.custo_acumulado?.toLocaleString("pt-BR")}</span>
                    <span>~{s.media_dias} dias/caso</span>
                  </div>
                  {/* Barra de capacidade */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-white rounded-full h-2 border border-gray-200">
                      <div
                        className={`h-2 rounded-full ${s.criticidade === "alta" ? "bg-red-500" : s.criticidade === "media" ? "bg-amber-400" : "bg-green-400"}`}
                        style={{ width: `${Math.min(100, s.pct_capacidade_reduzida)}%` }}
                      />
                    </div>
                    <span className={`text-xs font-bold flex-shrink-0 ${cfg.color}`}>
                      {s.pct_capacidade_reduzida}% reduzido
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
