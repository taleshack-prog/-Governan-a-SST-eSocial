// ==============================================================
// SST ESOCIAL GOV — Página: Trabalhadores
// Arquivo: frontend/src/pages/Trabalhadores.tsx
// ==============================================================

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";

const GES_OPCOES = [
  "GES1001 - Administração - Administrativo",
  "GES1002 - Administrativo - Acesso Produção",
  "GES1003 - Administração - Vendas",
  "GES1004 - Aprendiz - Senai",
  "GES2001 - Expedição/almoxarifado",
  "GES2002 - Expedição/almoxarifado - Liderança",
  "GES2003 - Expedição/almoxarifado - Encartelamento",
  "GES2004 - Portaria",
  "GES3001 - Ferramentaria",
  "GES3002 - Manutenção / Serralheria",
  "GES3003 - Estamparia - Operação Prensa",
  "GES3004 - Estamparia Progressiva",
  "GES3005 - Polimento",
  "GES3006 - Recebimento/preparação/Corte",
  "GES3007 - Solda",
  "GES3008 - Usinagem Tornos",
  "GES3009 - Escareação",
  "GES3010 - Gerência e Supervisão da Produção",
  "GES3011 - Montagem 1 (peças de linha)",
  "GES3012 - Montagem 1 Lavagem",
  "GES3013 - Montagem 2 (peças semi-pesadas)",
  "GES3014 - Ferramentaria Lavagem",
  "GES3015 - Vibroacabamento - Tratamento efluente",
  "GES3016 - Vibroacabamento",
];

const FORM_VAZIO = {
  nome: "", cpf: "", sexo: "M", pis_pasep: "",
  cargo: "", setor: "", matricula: "",
  data_admissao: "", data_nascimento: "", ges: "",
};

// Modal como componente EXTERNO para evitar bug de re-render
interface ModalProps {
  editando: any;
  form: any;
  setForm: (f: any) => void;
  onSalvar: () => void;
  onFechar: () => void;
  isPending: boolean;
}

function TrabalhadorModal({ editando, form, setForm, onSalvar, onFechar, isPending }: ModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-900 mb-4">
          {editando ? `Editar — ${editando.nome}` : "Novo Trabalhador"}
        </h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-600">Nome completo *</label>
            <input
              type="text"
              className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={form.nome}
              onChange={e => setForm({ ...form, nome: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">CPF *</label>
              <input
                type="text"
                placeholder="00000000000"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.cpf}
                onChange={e => setForm({ ...form, cpf: e.target.value.replace(/\D/g, "") })}
                maxLength={11}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Sexo</label>
              <select
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.sexo}
                onChange={e => setForm({ ...form, sexo: e.target.value })}
              >
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Cargo *</label>
              <input
                type="text"
                placeholder="Ex: Operador de Prensa"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.cargo}
                onChange={e => setForm({ ...form, cargo: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Matrícula</label>
              <input
                type="text"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.matricula}
                onChange={e => setForm({ ...form, matricula: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Grupo de Exposição Similar (GES) *</label>
            <select
              className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={form.setor}
              onChange={e => {
                const ges = e.target.value.split(" - ")[0];
                setForm({ ...form, setor: e.target.value, ges });
              }}
            >
              <option value="">Selecione o GES...</option>
              {GES_OPCOES.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600">Data de Admissão *</label>
              <input
                type="date"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.data_admissao}
                onChange={e => setForm({ ...form, data_admissao: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600">Data de Nascimento</label>
              <input
                type="date"
                className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={form.data_nascimento}
                onChange={e => setForm({ ...form, data_nascimento: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">PIS/PASEP</label>
            <input
              type="text"
              className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={form.pis_pasep}
              onChange={e => setForm({ ...form, pis_pasep: e.target.value.replace(/\D/g, "") })}
              maxLength={11}
            />
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
            disabled={!form.nome || !form.cpf || isPending}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {isPending ? "Salvando..." : editando ? "Salvar Alterações" : "Cadastrar"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function Trabalhadores() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState<any>(null);
  const [form, setForm] = useState<any>(FORM_VAZIO);

  const { data: trabalhadores = [], isLoading } = useQuery({
    queryKey: ["trabalhadores"],
    queryFn: () => apiClient.get("/trabalhadores/").then(r => r.data),
  });

  const criar = useMutation({
    mutationFn: (data: any) => apiClient.post("/trabalhadores/", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trabalhadores"] });
      setShowModal(false);
      setForm(FORM_VAZIO);
    },
  });

  const atualizar = useMutation({
    mutationFn: ({ id, data }: any) => apiClient.patch(`/trabalhadores/${id}/`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trabalhadores"] });
      setEditando(null);
      setForm(FORM_VAZIO);
    },
  });

  const abrirEdicao = (t: any) => {
    setEditando(t);
    setForm({
      nome: t.nome || "",
      cpf: t.cpf || "",
      sexo: t.sexo || "M",
      pis_pasep: t.pis_pasep || "",
      cargo: t.cargo || "",
      setor: t.setor || "",
      matricula: t.matricula || "",
      data_admissao: t.data_admissao || "",
      data_nascimento: t.data_nascimento || "",
      ges: t.ges || "",
    });
  };

  const salvar = () => {
    const payload = { ...form };
    if (!payload.data_admissao) delete payload.data_admissao;
    if (!payload.data_nascimento) delete payload.data_nascimento;
    if (editando) {
      atualizar.mutate({ id: editando.id, data: payload });
    } else {
      criar.mutate(payload);
    }
  };

  const fechar = () => {
    setShowModal(false);
    setEditando(null);
    setForm(FORM_VAZIO);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trabalhadores</h1>
          <p className="text-sm text-gray-500 mt-1">Cadastro e gestão dos trabalhadores vinculados à empresa</p>
        </div>
        <button
          onClick={() => { setShowModal(true); setEditando(null); setForm(FORM_VAZIO); }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + Novo Trabalhador
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Carregando...</div>
        ) : trabalhadores.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nenhum trabalhador cadastrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Nome","CPF","Cargo","Setor/GES","Admissão","Sexo",""].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {trabalhadores.map((t: any) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{t.nome}</td>
                  <td className="px-4 py-3 font-mono text-gray-600 text-xs">{t.cpf}</td>
                  <td className="px-4 py-3 text-gray-600">{t.cargo || <span className="text-red-400 text-xs">Não informado</span>}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{t.setor ? t.setor.split(" - ")[0] : <span className="text-red-400">Não informado</span>}</td>
                  <td className="px-4 py-3 text-gray-600">{t.data_admissao || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.sexo || "—"}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => abrirEdicao(t)}
                      className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {(showModal || editando) && (
        <TrabalhadorModal
          editando={editando}
          form={form}
          setForm={setForm}
          onSalvar={salvar}
          onFechar={fechar}
          isPending={criar.isPending || atualizar.isPending}
        />
      )}
    </div>
  );
}
