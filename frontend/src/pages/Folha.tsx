// ==============================================================
// SST ESOCIAL GOV — Página: Folha de Pagamento (lançamento de rubricas)
// Arquivo: frontend/src/pages/Folha.tsx
// ==============================================================

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface Estab { id: string; nome: string; codigo?: string; }
interface Rubrica {
  id: string;
  descricao: string;
  codigo_esocial: string | null;
  valor_mensal: number;
  incide_inss_praticado: boolean;
  incide_fgts_praticado: boolean;
  status_conciliacao: string;
}

const FORM_VAZIO = {
  descricao: "",
  codigo_esocial: "",
  natureza_declarada: "",
  valor_mensal: "",
  incide_inss_praticado: true,
  incide_fgts_praticado: true,
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function Folha() {
  const qc = useQueryClient();
  const [estabId, setEstabId] = useState<string>("");
  const [form, setForm] = useState<any>(FORM_VAZIO);

  const { data: estabs = [] } = useQuery<Estab[]>({
    queryKey: ["estabelecimentos"],
    queryFn: () => apiClient.get("/estabelecimentos/").then((r) => r.data),
  });

  const { data: rubricas = [], isLoading } = useQuery<Rubrica[]>({
    queryKey: ["rubricas", estabId],
    queryFn: () =>
      apiClient.get("/rubricas/", { params: { estabelecimento_id: estabId } }).then((r) => r.data),
    enabled: !!estabId,
  });

  const criar = useMutation({
    mutationFn: () =>
      apiClient.post("/rubricas/", {
        estabelecimento_id: estabId,
        descricao: form.descricao,
        codigo_esocial: form.codigo_esocial || null,
        natureza_declarada: form.natureza_declarada || null,
        valor_mensal: parseFloat(form.valor_mensal) || 0,
        incide_inss_praticado: form.incide_inss_praticado,
        incide_fgts_praticado: form.incide_fgts_praticado,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rubricas", estabId] });
      setForm(FORM_VAZIO);
    },
  });

  const totalFolha = rubricas.reduce((s, r) => s + (r.valor_mensal || 0), 0);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Folha de Pagamento</h1>
        <p className="text-gray-600 mt-1">
          Lance as rubricas da folha por estabelecimento. E a partir daqui que o comparador
          calcula creditos, travas e a fila de classificacao.
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-2xl p-4 mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-1">Estabelecimento</label>
        <select
          className="w-full border border-gray-300 rounded-xl p-2"
          value={estabId}
          onChange={(e) => setEstabId(e.target.value)}
        >
          <option value="">Selecione...</option>
          {estabs.map((e) => (
            <option key={e.id} value={e.id}>
              {e.nome} {e.codigo ? `(${e.codigo})` : ""}
            </option>
          ))}
        </select>
      </div>

      {estabId && (
        <>
          <div className="bg-white border border-gray-200 rounded-2xl p-4 mb-5">
            <h2 className="font-semibold text-gray-900 mb-3">Adicionar rubrica</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                className="border border-gray-300 rounded-xl p-2"
                placeholder="Descricao (ex.: Auxilio-alimentacao)"
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              />
              <input
                className="border border-gray-300 rounded-xl p-2"
                placeholder="Codigo eSocial (opcional)"
                value={form.codigo_esocial}
                onChange={(e) => setForm({ ...form, codigo_esocial: e.target.value })}
              />
              <input
                className="border border-gray-300 rounded-xl p-2"
                placeholder="Valor mensal (R$)"
                type="number"
                step="0.01"
                value={form.valor_mensal}
                onChange={(e) => setForm({ ...form, valor_mensal: e.target.value })}
              />
              <input
                className="border border-gray-300 rounded-xl p-2"
                placeholder="Natureza declarada (opcional)"
                value={form.natureza_declarada}
                onChange={(e) => setForm({ ...form, natureza_declarada: e.target.value })}
              />
            </div>
            <div className="flex flex-wrap gap-6 mt-3">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={form.incide_inss_praticado}
                  onChange={(e) => setForm({ ...form, incide_inss_praticado: e.target.checked })}
                />
                A empresa recolhe INSS sobre esta rubrica
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={form.incide_fgts_praticado}
                  onChange={(e) => setForm({ ...form, incide_fgts_praticado: e.target.checked })}
                />
                Recolhe FGTS
              </label>
            </div>
            <button
              onClick={() => criar.mutate()}
              disabled={criar.isPending || !form.descricao}
              className="mt-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 py-2 font-medium disabled:opacity-50"
            >
              {criar.isPending ? "Salvando..." : "Adicionar rubrica"}
            </button>
          </div>

          <div className="bg-white border border-gray-200 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900">Rubricas lancadas</h2>
              <span className="text-sm text-gray-500">
                Total: <strong>{brl(totalFolha)}</strong>/mes
              </span>
            </div>
            {isLoading && <p className="text-gray-500">Carregando...</p>}
            {!isLoading && rubricas.length === 0 && (
              <p className="text-gray-500 text-sm">Nenhuma rubrica lancada neste estabelecimento.</p>
            )}
            {rubricas.length > 0 && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2">Descricao</th>
                    <th className="py-2">Cod. eSocial</th>
                    <th className="py-2 text-right">Valor mensal</th>
                    <th className="py-2 text-center">INSS</th>
                    <th className="py-2 text-center">Conciliacao</th>
                  </tr>
                </thead>
                <tbody>
                  {rubricas.map((r) => (
                    <tr key={r.id} className="border-b last:border-0">
                      <td className="py-2 text-gray-900">{r.descricao}</td>
                      <td className="py-2 text-gray-500">{r.codigo_esocial || "-"}</td>
                      <td className="py-2 text-right text-gray-900">{brl(r.valor_mensal)}</td>
                      <td className="py-2 text-center">{r.incide_inss_praticado ? "Sim" : "Nao"}</td>
                      <td className="py-2 text-center">
                        <span className={r.status_conciliacao === "conciliada" ? "text-emerald-600" : "text-amber-600"}>
                          {r.status_conciliacao}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl p-3 text-sm text-blue-900">
            Depois de lancar a folha, va em <strong>Diagnostico</strong> e rode o comparador:
            ele gera os creditos e travas, e envia as rubricas condicionais para a <strong>Classificacao</strong>.
          </div>
        </>
      )}
    </div>
  );
}
