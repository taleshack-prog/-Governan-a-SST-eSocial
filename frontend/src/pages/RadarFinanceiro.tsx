// ==============================================================
// RADAR PREVIDENCIÁRIO — Tela WOW: Motor Financeiro
// Arquivo: frontend/src/pages/RadarFinanceiro.tsx
// ==============================================================
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { SectionTitle, Spinner } from "../components/ui";
import { TrendingDown, AlertTriangle, CheckCircle, Clock, Scale, HelpCircle } from "lucide-react";

const URGENCIA_CONFIG: Record<string, { color: string; bg: string }> = {
  alta:  { color: "text-red-700",    bg: "bg-red-50 border-red-200" },
  media: { color: "text-amber-700",  bg: "bg-amber-50 border-amber-200" },
  baixa: { color: "text-green-700",  bg: "bg-green-50 border-green-200" },
};

const STATUS_ICON: Record<string, any> = {
  limbo:           Scale,
  recebido:        Clock,
  em_analise:      Clock,
  em_beneficio:    CheckCircle,
  em_analise_inss: Clock,
  alta_inss:       CheckCircle,
};

function ScoreGauge({ score, nivel, cor, fatores }: any) {
  const pct = score / 100;
  const r = 70;
  const circ = Math.PI * r;
  const dash = circ * pct;

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col items-center">
      <div className="relative w-48 h-28 flex items-end justify-center">
        <svg width="192" height="112" viewBox="0 0 192 112">
          {/* Track */}
          <path
            d="M 16 96 A 80 80 0 0 1 176 96"
            fill="none" stroke="#f3f4f6" strokeWidth="14" strokeLinecap="round"
          />
          {/* Score arc */}
          <path
            d="M 16 96 A 80 80 0 0 1 176 96"
            fill="none"
            stroke={cor}
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={`${(circ * pct).toFixed(1)} ${circ}`}
            style={{ transition: "stroke-dasharray 1s ease" }}
          />
        </svg>
        <div className="absolute bottom-2 text-center">
          <div className="text-4xl font-bold" style={{ color: cor }}>{score}</div>
          <div className="text-xs font-semibold uppercase tracking-wider mt-0.5" style={{ color: cor }}>{nivel}</div>
        </div>
      </div>

      <p className="text-sm font-semibold text-gray-700 mt-3 mb-3">Score de Pressão Previdenciária</p>

      {fatores.length > 0 && (
        <div className="w-full space-y-1.5 mt-1">
          {fatores.map((f: string, i: number) => (
            <div key={i} className="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-1.5">
              <AlertTriangle size={12} className="text-amber-500 flex-shrink-0" />
              {f}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function RadarFinanceiro() {
  const { data: score, isLoading: loadingScore } = useQuery({
    queryKey: ["radar-score"],
    queryFn: () => apiClient.get("/radar-financeiro/score").then(r => r.data),
    refetchInterval: 30000,
  });

  const { data: perdas, isLoading: loadingPerdas } = useQuery({
    queryKey: ["radar-perdas"],
    queryFn: () => apiClient.get("/radar-financeiro/perdas-evitageis").then(r => r.data),
    refetchInterval: 30000,
  });

  const { data: rec, isLoading: loadingRec } = useQuery({
    queryKey: ["radar-rec"],
    queryFn: () => apiClient.get("/radar-financeiro/recomendacoes").then(r => r.data),
    refetchInterval: 30000,
  });

  const isLoading = loadingScore || loadingPerdas || loadingRec;

  if (isLoading) return (
    <div className="flex justify-center items-center h-64"><Spinner size={32} /></div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <SectionTitle
          title="Radar Financeiro"
          subtitle="Perdas evitáveis, recomendações e score de pressão"
        />
        <div className="text-xs text-gray-400 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
          Atualizado agora
        </div>
      </div>

      {/* KPIs topo */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Custo diário atual</p>
          <p className="text-2xl font-bold text-red-600">
            R$ {rec?.custo_diario?.toLocaleString("pt-BR") || "0"}
          </p>
          <p className="text-xs text-gray-400 mt-1">por dia em afastamentos</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Projeção fim do mês</p>
          <p className="text-2xl font-bold text-orange-600">
            R$ {rec?.projecao_fim_mes?.toLocaleString("pt-BR") || "0"}
          </p>
          <p className="text-xs text-gray-400 mt-1">se nada mudar</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Perdas evitáveis</p>
          <p className="text-2xl font-bold text-amber-600">
            R$ {perdas?.total_recuperavel?.toLocaleString("pt-BR") || "0"}
          </p>
          <p className="text-xs text-gray-400 mt-1">recuperáveis com ação</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Casos ativos</p>
          <p className="text-2xl font-bold text-[#0f2744]">{score?.ativos || 0}</p>
          <p className="text-xs text-gray-400 mt-1">de {score?.total_trabalhadores || 0} trabalhadores</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* Score */}
        {score && (
          <ScoreGauge
            score={score.score}
            nivel={score.nivel}
            cor={score.cor}
            fatores={score.fatores}
          />
        )}

        {/* Recomendações */}
        <div className="xl:col-span-2 bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[#0f2744] rounded-lg flex items-center justify-center">
              <TrendingDown size={16} color="white" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">Faça isso agora</p>
              <p className="text-xs text-gray-400">Recomendações por impacto financeiro</p>
            </div>
          </div>

          <div className="space-y-3">
            {rec?.recomendacoes?.map((r: any) => {
              const cfg = URGENCIA_CONFIG[r.urgencia] || URGENCIA_CONFIG.baixa;
              return (
                <div key={r.prioridade} className={`flex items-start gap-3 rounded-xl p-3.5 border ${cfg.bg}`}>
                  <div className="w-7 h-7 rounded-full bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                    <span className="text-sm">{r.icone}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className={`text-sm font-semibold ${cfg.color}`}>{r.acao}</p>
                      <span className="text-xs font-bold text-green-700 bg-green-50 px-2 py-0.5 rounded-full whitespace-nowrap border border-green-200">
                        R$ {r.impacto_estimado?.toLocaleString("pt-BR")}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{r.detalhe}</p>
                  </div>
                </div>
              );
            })}

            {(!rec?.recomendacoes || rec.recomendacoes.length === 0) && (
              <div className="text-center py-8 text-gray-400 text-sm">
                <CheckCircle size={32} className="mx-auto mb-2 text-green-400" />
                Nenhuma ação urgente no momento.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Perdas evitáveis */}
      {perdas?.casos?.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center">
              <AlertTriangle size={16} color="white" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">Perdas Evitáveis</p>
              <p className="text-xs text-gray-400">
                Total recuperável: <span className="font-bold text-amber-600">R$ {perdas.total_recuperavel?.toLocaleString("pt-BR")}</span>
              </p>
            </div>
          </div>

          <div className="space-y-2">
            {perdas.casos.map((c: any, i: number) => {
              const cfg = URGENCIA_CONFIG[c.urgencia] || URGENCIA_CONFIG.baixa;
              return (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 border border-gray-100">
                  <div className="w-9 h-9 rounded-xl bg-[#0f2744] flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs font-bold">
                      {c.trabalhador.split(" ").map((n: string) => n[0]).join("").slice(0, 2)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900">{c.trabalhador}</p>
                    <p className="text-xs text-gray-500">{c.setor} · {c.dias_afastado} dias afastado</p>
                    <p className="text-xs text-gray-600 mt-0.5">{c.acao}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-sm font-bold text-amber-600">R$ {c.perda_evitavel?.toLocaleString("pt-BR")}</p>
                    <p className="text-xs text-gray-400">evitável</p>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.color} ${cfg.bg} border`}>
                      {c.urgencia}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
