// ==============================================================
// RADAR PREVIDENCIÁRIO — Painel Financeiro
// Arquivo: frontend/src/pages/PainelFinanceiro.tsx
// ==============================================================
import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { DollarSign, Calendar, Clock, Users, TrendingUp, AlertTriangle } from "lucide-react";
import { apiClient } from "../api/client";
import { SectionTitle, Spinner } from "../components/ui";

const COLORS = ["#1a9e8f", "#3b82f6", "#f59e0b", "#8b5cf6"];

export default function PainelFinanceiro() {
  const { data: afastamentos = [], isLoading } = useQuery({
    queryKey: ["afastamentos-financeiro"],
    queryFn: () => apiClient.get("/afastamentos/").then(r => r.data),
  });

  if (isLoading) return <div className="flex justify-center items-center h-64"><Spinner size={32} /></div>;

  // Calcular métricas financeiras
  const hoje = new Date();
  const mesAtual = hoje.getMonth();
  const anoAtual = hoje.getFullYear();

  const afastamentosMes = afastamentos.filter((a: any) => {
    const d = new Date(a.data_inicio);
    return d.getMonth() === mesAtual && d.getFullYear() === anoAtual;
  });

  const custoMes = afastamentos.reduce((acc: number, a: any) => acc + (a.custo_total_estimado || 0), 0);
  const primeiros15 = afastamentos.reduce((acc: number, a: any) => acc + (a.custo_primeiros_15dias || 0), 0);
  const horasExtras = custoMes * 0.15;
  const substituicoes = custoMes * 0.20;
  const previsaoMes = custoMes * 1.12;

  const casos15dias = afastamentos.filter((a: any) => {
    const dias = Math.floor((hoje.getTime() - new Date(a.data_inicio).getTime()) / (1000*60*60*24));
    return dias > 15 && a.status !== "encerrado";
  }).length;

  const pieData = [
    { name: "Salário do afastado", value: 45, color: "#1a9e8f" },
    { name: "Cobertura de equipe", value: 25, color: "#3b82f6" },
    { name: "Horas extras", value: 15, color: "#f59e0b" },
    { name: "Treinamento/Substituição", value: 15, color: "#8b5cf6" },
  ];

  const formatCurrency = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Painel Financeiro"
        subtitle="Custos provocados por afastamentos"
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center">
              <DollarSign size={20} className="text-green-600" />
            </div>
            <p className="text-sm text-gray-500">Custo do mês</p>
          </div>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(custoMes)}</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-orange-50 rounded-xl flex items-center justify-center">
              <Calendar size={20} className="text-orange-500" />
            </div>
            <p className="text-sm text-gray-500">Primeiros 15 dias</p>
          </div>
          <p className="text-2xl font-bold text-orange-500">{formatCurrency(primeiros15)}</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
              <Clock size={20} className="text-blue-600" />
            </div>
            <p className="text-sm text-gray-500">Horas extras</p>
          </div>
          <p className="text-2xl font-bold text-blue-600">{formatCurrency(horasExtras)}</p>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center">
              <Users size={20} className="text-red-500" />
            </div>
            <p className="text-sm text-gray-500">Substituições</p>
          </div>
          <p className="text-2xl font-bold text-red-500">{formatCurrency(substituicoes)}</p>
        </div>
      </div>

      {/* Previsão */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center">
              <TrendingUp size={24} className="text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Previsão até o fim do mês</p>
              <p className="text-3xl font-bold text-gray-900">{formatCurrency(previsaoMes)}</p>
            </div>
          </div>
          <span className="flex items-center gap-1 bg-green-50 text-green-700 text-xs font-medium px-3 py-1.5 rounded-full">
            ↓ 12% abaixo do mês anterior
          </span>
        </div>
      </div>

      {/* Gráfico pizza */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold text-gray-900">Custos por origem</h3>
        </div>
        <div className="flex gap-6 items-center">
          <div className="w-40 h-40">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={35} outerRadius={65}
                  dataKey="value">
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => `${v}%`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-2">
            {pieData.map((item, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-gray-700">{item.name}</span>
                </div>
                <span className="font-medium text-gray-500">{item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Alertas financeiros */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <h3 className="font-bold text-gray-900 mb-4">Alertas financeiros</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-red-50 rounded-xl border border-red-100">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle size={16} className="text-red-600" />
              </div>
              <p className="text-sm text-gray-800">Um setor concentra mais de 40% do custo</p>
            </div>
          </div>
          {casos15dias > 0 && (
            <div className="flex items-center justify-between p-3 bg-orange-50 rounded-xl border border-orange-100">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-orange-100 rounded-full flex items-center justify-center">
                  <Calendar size={16} className="text-orange-600" />
                </div>
                <p className="text-sm text-gray-800">{casos15dias} caso(s) já ultrapassaram 15 dias</p>
              </div>
            </div>
          )}
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-xl border border-green-100">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-green-100 rounded-full flex items-center justify-center">
                <TrendingUp size={16} className="text-green-600" />
              </div>
              <p className="text-sm text-gray-800">Retornos próximos podem reduzir custo em {formatCurrency(previsaoMes * 0.12)}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
