// ==============================================================
// RADAR PREVIDENCIÁRIO — Painel Admin (Multi-empresa)
// Arquivo: frontend/src/pages/Admin.tsx
// ==============================================================
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Users, CheckCircle, XCircle, Plus, Crown } from "lucide-react";
import { apiClient } from "../api/client";
import { SectionTitle, Spinner } from "../components/ui";

const PLANOS = {
  trial:        { label: "Trial",        color: "bg-gray-100 text-gray-600" },
  basico:       { label: "Básico",       color: "bg-blue-100 text-blue-700" },
  profissional: { label: "Profissional", color: "bg-purple-100 text-purple-700" },
  enterprise:   { label: "Enterprise",   color: "bg-yellow-100 text-yellow-700" },
};

export default function Admin() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    razao_social: "", cnpj: "", cnae_principal: "47110",
    grau_risco: 1, plano: "trial",
    contato_nome: "", contato_email: "", contato_telefone: "",
    admin_senha: "Radar@2026"
  });

  const { data: empresas = [], isLoading } = useQuery({
    queryKey: ["admin-empresas"],
    queryFn: () => apiClient.get("/admin/empresas").then(r => r.data),
  });

  const cadastrar = useMutation({
    mutationFn: (data: any) => apiClient.post("/admin/empresas", data).then(r => r.data),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["admin-empresas"] });
      setShowForm(false);
      alert(`✅ Empresa cadastrada!\n\nEmail: ${result.admin_email}\nSenha: ${result.admin_senha}\n\nEnvie essas credenciais para o cliente.`);
    },
    onError: (e: any) => alert("Erro: " + (e.response?.data?.detail || "Tente novamente")),
  });

  const toggleAtivo = useMutation({
    mutationFn: (id: string) => apiClient.patch(`/admin/empresas/${id}/ativar`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-empresas"] }),
  });

  const formatCNPJ = (v: string) => v.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");

  if (isLoading) return <div className="flex justify-center items-center h-64"><Spinner size={32} /></div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <SectionTitle title="Painel Admin" subtitle="Gerenciamento de clientes SaaS" />
        <button onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-[#0f2744] text-white px-4 py-2 rounded-lg text-sm font-medium">
          <Plus size={16} />
          Nova Empresa
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500">Total clientes</p>
          <p className="text-3xl font-bold text-[#0f2744]">{empresas.length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500">Ativos</p>
          <p className="text-3xl font-bold text-green-600">{empresas.filter((e: any) => e.ativo).length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500">Trial</p>
          <p className="text-3xl font-bold text-gray-500">{empresas.filter((e: any) => e.plano === "trial").length}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500">Pagantes</p>
          <p className="text-3xl font-bold text-blue-600">{empresas.filter((e: any) => e.plano !== "trial").length}</p>
        </div>
      </div>

      {/* Formulário */}
      {showForm && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-blue-200">
          <h3 className="font-bold text-gray-900 mb-4">Cadastrar Nova Empresa</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: "Razão Social", key: "razao_social", type: "text" },
              { label: "CNPJ", key: "cnpj", type: "text" },
              { label: "CNAE Principal", key: "cnae_principal", type: "text" },
              { label: "Nome do Contato", key: "contato_nome", type: "text" },
              { label: "Email do Admin", key: "contato_email", type: "email" },
              { label: "Telefone", key: "contato_telefone", type: "text" },
              { label: "Senha Inicial", key: "admin_senha", type: "text" },
            ].map(f => (
              <div key={f.key}>
                <label className="text-xs font-medium text-gray-600 block mb-1">{f.label}</label>
                <input type={f.type} value={(form as any)[f.key]}
                  onChange={e => setForm({...form, [f.key]: e.target.value})}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            ))}
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Plano</label>
              <select value={form.plano} onChange={e => setForm({...form, plano: e.target.value})}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="trial">Trial (15 dias)</option>
                <option value="basico">Básico — R$ 297/mês</option>
                <option value="profissional">Profissional — R$ 697/mês</option>
                <option value="enterprise">Enterprise — R$ 1.497/mês</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Grau de Risco</label>
              <select value={form.grau_risco} onChange={e => setForm({...form, grau_risco: parseInt(e.target.value)})}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value={1}>GR 1</option>
                <option value={2}>GR 2</option>
                <option value={3}>GR 3</option>
                <option value={4}>GR 4</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button onClick={() => cadastrar.mutate(form)} disabled={cadastrar.isPending}
              className="bg-[#0f2744] text-white px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-50">
              {cadastrar.isPending ? "Cadastrando..." : "Cadastrar"}
            </button>
            <button onClick={() => setShowForm(false)}
              className="border border-gray-300 text-gray-600 px-5 py-2 rounded-lg text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Lista de empresas */}
      <div className="space-y-3">
        {empresas.map((e: any) => (
          <div key={e.id} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#0f2744] rounded-xl flex items-center justify-center">
                  <Building2 size={18} color="white" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900 text-sm">{e.razao_social}</p>
                    {e.plano !== "trial" && <Crown size={12} className="text-yellow-500" />}
                  </div>
                  <p className="text-xs text-gray-500">CNPJ: {formatCNPJ(e.cnpj)} • {e.contato_email || "—"}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${(PLANOS as any)[e.plano]?.color || "bg-gray-100 text-gray-600"}`}>
                      {(PLANOS as any)[e.plano]?.label || e.plano}
                    </span>
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <Users size={10} /> {e.n_trabalhadores} trabalhadores
                    </span>
                    {e.plano_expira_em && (
                      <span className="text-xs text-gray-400">Expira: {new Date(e.plano_expira_em).toLocaleDateString("pt-BR")}</span>
                    )}
                  </div>
                </div>
              </div>
              <button onClick={() => toggleAtivo.mutate(e.id)}
                className={`flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg font-medium ${e.ativo ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"}`}>
                {e.ativo ? <><CheckCircle size={12} /> Ativo</> : <><XCircle size={12} /> Inativo</>}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
