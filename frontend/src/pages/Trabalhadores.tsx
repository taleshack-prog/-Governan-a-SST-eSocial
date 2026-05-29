// ==============================================================
// SST ESOCIAL GOV — Página: Trabalhadores
// Arquivo: frontend/src/pages/Trabalhadores.tsx
// ==============================================================

import { useState } from "react";
import { UserPlus } from "lucide-react";
import { useTrabalhadores, useCriarTrabalhador } from "../hooks/useQueries";
import { Card, SectionTitle, Spinner, EmptyState } from "../components/ui";

export function Trabalhadores() {
  const [showForm, setShowForm] = useState(false);
  const { data: lista = [], isLoading } = useTrabalhadores();
  const criar = useCriarTrabalhador();
  const [form, setForm] = useState({ cpf: "", nome: "", sexo: "M", pis_pasep: "" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await criar.mutateAsync(form);
    setShowForm(false);
    setForm({ cpf: "", nome: "", sexo: "M", pis_pasep: "" });
  }

  return (
    <div>
      <SectionTitle title="Trabalhadores" subtitle="Cadastro e gestão dos trabalhadores vinculados à empresa" />

      <div className="flex mb-6">
        <button
          onClick={() => setShowForm(!showForm)}
          className="ml-auto flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <UserPlus size={16} />
          Novo Trabalhador
        </button>
      </div>

      {showForm && (
        <Card className="mb-6 border-indigo-200 bg-indigo-50">
          <h3 className="font-semibold text-gray-800 mb-4">Cadastrar Trabalhador</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: "CPF *", key: "cpf", placeholder: "00000000000" },
              { label: "Nome Completo *", key: "nome", placeholder: "Nome do trabalhador" },
              { label: "PIS/PASEP", key: "pis_pasep", placeholder: "00000000000" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                <input
                  value={(form as any)[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  placeholder={placeholder}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  required={label.includes("*")}
                />
              </div>
            ))}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Sexo</label>
              <select value={form.sexo} onChange={(e) => setForm({ ...form, sexo: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
                <option value="O">Outro</option>
              </select>
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" disabled={criar.isPending}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50">
                {criar.isPending ? "Salvando..." : "Cadastrar"}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="text-sm text-gray-600 px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50">
                Cancelar
              </button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        {isLoading ? <div className="flex justify-center py-12"><Spinner /></div> :
          lista.length === 0 ? <EmptyState message="Nenhum trabalhador cadastrado." /> : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Nome</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">CPF</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((t: any) => (
                  <tr key={t.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-3 font-medium text-gray-800">{t.nome}</td>
                    <td className="py-3 px-3 text-gray-500 font-mono">{t.cpf}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </Card>
    </div>
  );
}
