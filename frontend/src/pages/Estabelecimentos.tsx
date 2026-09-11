// ==============================================================
// SST ESOCIAL GOV — Página: Estabelecimentos
// Arquivo: frontend/src/pages/Estabelecimentos.tsx
// ==============================================================

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";

const FORM_VAZIO = {
  codigo: "", nome: "", tipo_estabelecimento: "CNPJ", posicao: "filial",
  cnpj: "", identificador: "", cnae: "", grau_risco: "", aliquota_rat: "",
  fpas: "", atividade_descrita: "", status: "ativa", cidade: "", uf: "",
};

// Modal como componente EXTERNO para evitar bug de re-render
interface ModalProps {
  form: any;
  setForm: (f: any) => void;
  onSalvar: () => void;
  onFechar: () => void;
  isPending: boolean;
}

function EstabelecimentoModal({ form, setForm, onSalvar, onFechar, isPending }: ModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Novo Estabelecimento</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Código *</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.codigo}
                onChange={e => setForm({ ...form, codigo: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Nome *</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.nome}
                onChange={e => setForm({ ...form, nome: e.target.value })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Natureza</label>
              <select
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.tipo_estabelecimento}
                onChange={e => setForm({ ...form, tipo_estabelecimento: e.target.value })}
              >
                <option value="CNPJ">CNPJ</option>
                <option value="CNO">CNO</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Posição</label>
              <select
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.posicao}
                onChange={e => setForm({ ...form, posicao: e.target.value })}
              >
                <option value="matriz">Matriz</option>
                <option value="filial">Filial</option>
              </select>
            </div>
          </div>
          {form.tipo_estabelecimento === "CNPJ" ? (
            <div>
              <label className="text-xs font-medium text-gray-600">CNPJ</label>
              <input
                type="text"
                placeholder="00000000000000"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.cnpj}
                onChange={e => setForm({ ...form, cnpj: e.target.value.replace(/\D/g, "") })}
                maxLength={14}
              />
            </div>
          ) : (
            <div>
              <label className="text-xs font-medium text-gray-600">Identificador (CNO)</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.identificador}
                onChange={e => setForm({ ...form, identificador: e.target.value })}
              />
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">CNAE</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.cnae}
                onChange={e => setForm({ ...form, cnae: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Grau de Risco</label>
              <select
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.grau_risco}
                onChange={e => setForm({ ...form, grau_risco: e.target.value })}
              >
                <option value="">Selecione...</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Alíquota RAT (%)</label>
              <input
                type="number"
                step="0.01"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.aliquota_rat}
                onChange={e => setForm({ ...form, aliquota_rat: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">FPAS</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.fpas}
                onChange={e => setForm({ ...form, fpas: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Atividade Descrita</label>
            <input
              type="text"
              className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={form.atividade_descrita}
              onChange={e => setForm({ ...form, atividade_descrita: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Status</label>
              <select
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.status}
                onChange={e => setForm({ ...form, status: e.target.value })}
              >
                <option value="ativa">Ativa</option>
                <option value="paralisada">Paralisada</option>
                <option value="encerrada">Encerrada</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Cidade</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.cidade}
                onChange={e => setForm({ ...form, cidade: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">UF</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.uf}
                onChange={e => setForm({ ...form, uf: e.target.value.toUpperCase() })}
                maxLength={2}
              />
            </div>
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <button
            onClick={onFechar}
            className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={onSalvar}
            disabled={!form.codigo || !form.nome || isPending}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {isPending ? "Salvando..." : "Cadastrar"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function Estabelecimentos() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [fapEstab, setFapEstab] = useState<any>(null);
  const [fapValores, setFapValores] = useState<Record<number, string>>({});
  const [fapSalvando, setFapSalvando] = useState(false);
  const ANOS_FAP = [2021, 2022, 2023, 2024, 2025, 2026];

  const abrirFap = async (e: any) => {
    setFapEstab(e);
    try {
      const resp = await apiClient.get(`/estabelecimentos/${e.id}/fap`);
      const mapa: Record<number, string> = {};
      (resp.data || []).forEach((r: any) => { mapa[r.ano] = String(r.fap); });
      setFapValores(mapa);
    } catch { setFapValores({}); }
  };

  const salvarFap = async () => {
    if (!fapEstab) return;
    setFapSalvando(true);
    try {
      const faps = ANOS_FAP
        .filter(ano => fapValores[ano] !== undefined && fapValores[ano] !== "")
        .map(ano => ({ ano, fap: Number(fapValores[ano]) }));
      await apiClient.put(`/estabelecimentos/${fapEstab.id}/fap`, faps);
      setFapEstab(null);
    } catch {
      alert("Não foi possível salvar o FAP.");
    } finally {
      setFapSalvando(false);
    }
  };
  const [form, setForm] = useState<any>(FORM_VAZIO);

  const { data: estabelecimentos = [], isLoading } = useQuery({
    queryKey: ["estabelecimentos"],
    queryFn: () => apiClient.get("/estabelecimentos/").then(r => r.data),
  });

  const criar = useMutation({
    mutationFn: (data: any) => apiClient.post("/estabelecimentos/", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["estabelecimentos"] });
      setShowModal(false);
      setForm(FORM_VAZIO);
    },
    onError: (e: any) => alert("Erro: " + (e.response?.data?.detail || "Tente novamente")),
  });

  const salvar = () => {
    const payload: any = { ...form };
    if (!payload.cnpj) delete payload.cnpj;
    if (!payload.identificador) delete payload.identificador;
    if (!payload.cnae) delete payload.cnae;
    if (!payload.fpas) delete payload.fpas;
    if (!payload.atividade_descrita) delete payload.atividade_descrita;
    if (!payload.cidade) delete payload.cidade;
    if (!payload.uf) delete payload.uf;
    payload.grau_risco = payload.grau_risco ? Number(payload.grau_risco) : null;
    payload.aliquota_rat = payload.aliquota_rat ? Number(payload.aliquota_rat) : null;
    criar.mutate(payload);
  };

  const fechar = () => {
    setShowModal(false);
    setForm(FORM_VAZIO);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Estabelecimentos</h1>
          <p className="text-sm text-gray-500 mt-1">Cadastro dos estabelecimentos (matriz e filiais) da empresa</p>
        </div>
        <button
          onClick={() => { setShowModal(true); setForm(FORM_VAZIO); }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + Novo Estabelecimento
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Carregando...</div>
        ) : estabelecimentos.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nenhum estabelecimento cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Código", "Nome", "Natureza", "Posição", "CNAE", "RAT%", "Status", "FAP/ano"].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {estabelecimentos.map((e: any) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-600 text-xs">{e.codigo}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{e.nome}</td>
                  <td className="px-4 py-3 text-gray-600">{e.tipo_estabelecimento}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{e.posicao}</td>
                  <td className="px-4 py-3 text-gray-600">{e.cnae || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{e.aliquota_rat ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{e.status}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => abrirFap(e)}
                      className="text-indigo-600 hover:text-indigo-800 text-xs font-medium">
                      📊 FAP/ano
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <EstabelecimentoModal
          form={form}
          setForm={setForm}
          onSalvar={salvar}
          onFechar={fechar}
          isPending={criar.isPending}
        />
      )}
      {fapEstab && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold text-gray-900">FAP por ano</h2>
            <p className="text-xs text-gray-500 mt-1 mb-4">
              {fapEstab.nome} — o cálculo retroativo usa o FAP de cada ano, não o atual. Preencha todos os anos disponíveis.
            </p>
            <div className="space-y-2">
              {ANOS_FAP.map(ano => (
                <div key={ano} className="flex items-center gap-3">
                  <label className="w-16 text-sm text-gray-600">{ano}</label>
                  <input type="number" step="0.01" min="0.5" max="2.0"
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-500"
                    value={fapValores[ano] ?? ""}
                    onChange={ev => setFapValores(v => ({ ...v, [ano]: ev.target.value }))}
                    placeholder="0.50 a 2.00" />
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setFapEstab(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancelar</button>
              <button onClick={salvarFap} disabled={fapSalvando}
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
                {fapSalvando ? "Salvando…" : "Salvar FAP"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
