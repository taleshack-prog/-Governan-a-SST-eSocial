// ==============================================================
// RADAR PREVIDENCIÁRIO — Painel do Gestor
// Arquivo: frontend/src/pages/PainelGestor.tsx
// ==============================================================
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Users, Calendar, HelpCircle, CheckCircle, Clock, AlertTriangle } from "lucide-react";
import { apiClient } from "../api/client";
import { SectionTitle, Spinner } from "../components/ui";

export default function PainelGestor() {
  const { data: afastamentos = [], isLoading } = useQuery({
    queryKey: ["afastamentos-gestor"],
    queryFn: () => apiClient.get("/afastamentos/").then(r => r.data),
  });

  const { data: trabalhadores = [] } = useQuery({
    queryKey: ["trabalhadores-gestor"],
    queryFn: () => apiClient.get("/trabalhadores/").then(r => r.data),
  });

  if (isLoading) return <div className="flex justify-center items-center h-64"><Spinner size={32} /></div>;

  const hoje = new Date();

  const ativos = afastamentos.filter((a: any) => a.status !== "encerrado");
  const comRetorno = ativos.filter((a: any) => a.data_prevista_retorno);
  const semRetorno = ativos.filter((a: any) => !a.data_prevista_retorno);

  const retornosEstaSemana = ativos.filter((a: any) => {
    if (!a.data_prevista_retorno) return false;
    const retorno = new Date(a.data_prevista_retorno);
    const diff = (retorno.getTime() - hoje.getTime()) / (1000*60*60*24);
    return diff >= 0 && diff <= 7;
  });

  // Afastados por setor
  const setores: Record<string, { comPrevisao: number; semPrevisao: number }> = {};
  ativos.forEach((a: any) => {
    const setor = a.setor || a.trabalhador_setor || "Geral";
    if (!setores[setor]) setores[setor] = { comPrevisao: 0, semPrevisao: 0 };
    if (a.data_prevista_retorno) setores[setor].comPrevisao++;
    else setores[setor].semPrevisao++;
  });

  const barData = Object.entries(setores).map(([setor, v]) => ({
    setor: setor.length > 12 ? setor.slice(0, 12) + "..." : setor,
    "Com previsão": v.comPrevisao,
    "Sem previsão": v.semPrevisao,
  }));

  const getStatusRetorno = (a: any) => {
    if (!a.data_prevista_retorno) return { label: "Sem previsão", color: "red", bg: "bg-red-50 text-red-600" };
    const diff = (new Date(a.data_prevista_retorno).getTime() - hoje.getTime()) / (1000*60*60*24);
    if (diff < 0) return { label: "Atrasado", color: "red", bg: "bg-red-50 text-red-600" };
    if (diff <= 2) return { label: "Retorna amanhã", color: "blue", bg: "bg-blue-50 text-blue-600" };
    if (diff <= 7) return { label: `Retorna em ${Math.ceil(diff)} dias`, color: "green", bg: "bg-green-50 text-green-600" };
    return { label: "Provável", color: "gray", bg: "bg-gray-50 text-gray-600" };
  };

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Painel do Gestor"
        subtitle="Visão da equipe e previsões de retorno"
      />

      {/* Card equipe */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-teal-50 rounded-xl flex items-center justify-center">
              <Users size={20} className="text-teal-600" />
            </div>
            <p className="font-bold text-gray-900">Equipe — {trabalhadores.length} trabalhadores</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
          <div className="text-center">
            <p className="text-3xl font-bold text-teal-600">{ativos.length}</p>
            <p className="text-xs text-gray-500 mt-1">Afastados</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-blue-600">{retornosEstaSemana.length}</p>
            <p className="text-xs text-gray-500 mt-1">Retornos esta semana</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-orange-500">{semRetorno.length}</p>
            <p className="text-xs text-gray-500 mt-1">Sem previsão</p>
          </div>
        </div>
      </div>

      {/* Afastados por setor */}
      {barData.length > 0 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-bold text-gray-900 mb-4">Afastados por setor</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="setor" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="Com previsão" stackId="a" fill="#1a9e8f" radius={[0,0,0,0]} />
              <Bar dataKey="Sem previsão" stackId="a" fill="#a7f3d0" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Retornos previstos */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold text-gray-900">Retornos previstos</h3>
        </div>
        {ativos.length === 0 ? (
          <p className="text-sm text-gray-400">Nenhum afastamento ativo.</p>
        ) : (
          <div className="space-y-3">
            {ativos.slice(0, 5).map((a: any) => {
              const st = getStatusRetorno(a);
              return (
                <div key={a.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-teal-600 flex items-center justify-center text-white text-xs font-bold">
                      {a.trabalhador_nome?.split(" ").map((n: string) => n[0]).slice(0,2).join("")}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{a.trabalhador_nome}</p>
                      <p className="text-xs text-gray-500">{a.trabalhador_setor || "—"}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${st.bg}`}>
                      {st.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Impacto operacional */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <h3 className="font-bold text-gray-900 mb-4">Impacto operacional</h3>
        <div className="grid grid-cols-3 gap-3">
          {ativos.length > 2 && (
            <div className="bg-green-50 rounded-xl p-3 text-center">
              <AlertTriangle size={20} className="text-green-600 mx-auto mb-1" />
              <p className="text-xs text-gray-700 font-medium">Alta atenção</p>
            </div>
          )}
          <div className="bg-blue-50 rounded-xl p-3 text-center">
            <Calendar size={20} className="text-blue-600 mx-auto mb-1" />
            <p className="text-xs text-gray-700 font-medium">Escala precisa de ajuste</p>
          </div>
          <div className="bg-orange-50 rounded-xl p-3 text-center">
            <Users size={20} className="text-orange-600 mx-auto mb-1" />
            <p className="text-xs text-gray-700 font-medium">Substituição recomendada</p>
          </div>
        </div>
      </div>
    </div>
  );
}
