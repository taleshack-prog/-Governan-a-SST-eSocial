import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  recebido:               { label: "Recebido",               color: "bg-blue-100 text-blue-800" },
  em_analise:             { label: "Em Análise",             color: "bg-yellow-100 text-yellow-800" },
  pendente:               { label: "Pendente",               color: "bg-orange-100 text-orange-800" },
  em_andamento:           { label: "Em Andamento",           color: "bg-purple-100 text-purple-800" },
  retorno_proximo:        { label: "Retorno Próximo",        color: "bg-teal-100 text-teal-800" },
  aguardando_confirmacao: { label: "Aguard. Confirmação",    color: "bg-cyan-100 text-cyan-800" },
  encerrado:              { label: "Encerrado",              color: "bg-gray-100 text-gray-800" },
  reaberto:               { label: "Reaberto",               color: "bg-red-100 text-red-800" },
  em_beneficio:           { label: "Em Benefício",           color: "bg-green-100 text-green-800" },
  em_analise_inss:        { label: "Em Análise INSS",        color: "bg-yellow-100 text-yellow-900" },
  limbo:                  { label: "Limbo (Via Judicial)",   color: "bg-red-100 text-red-900" },
  alta_inss:              { label: "Alta INSS",              color: "bg-indigo-100 text-indigo-800" },
};

const TIPO_LABELS: Record<string, string> = {
  doenca:            "Doença",
  acidente:          "Acidente",
  acidente_trabalho: "Acidente de Trabalho",
  maternidade:       "Maternidade",
  outros:            "Outros",
};

export default function Afastamentos() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [filtroStatus, setFiltroStatus] = useState("");
  const [detalhe, setDetalhe] = useState<any>(null);
  const [uploadando, setUploadando] = useState(false);
  const [resultadoAtestado, setResultadoAtestado] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadAtestado = async (file: File, afastamentoId: string) => {
    setUploadando(true);
    setResultadoAtestado(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const resp = await apiClient.post(`/afastamentos/${afastamentoId}/atestados/`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResultadoAtestado(resp.data);
      qc.invalidateQueries({ queryKey: ["afastamentos"] });
      qc.invalidateQueries({ queryKey: ["afastamentos-kpis"] });
    } catch {
      setResultadoAtestado({ erro: "Erro ao enviar atestado" });
    } finally {
      setUploadando(false);
    }
  };

  const { data: kpis } = useQuery({
    queryKey: ["afastamentos-kpis"],
    queryFn: () => apiClient.get("/afastamentos/kpis/").then(r => r.data),
  });

  const { data: afastamentos = [], isLoading } = useQuery({
    queryKey: ["afastamentos", filtroStatus],
    queryFn: () => apiClient.get("/afastamentos/", {
      params: filtroStatus ? { status: filtroStatus } : {}
    }).then(r => r.data),
  });

  const { data: trabalhadores = [] } = useQuery({
    queryKey: ["trabalhadores"],
    queryFn: () => apiClient.get("/trabalhadores/").then(r => r.data),
  });

  const [form, setForm] = useState({
    trabalhador_id: "", tipo: "doenca",
    data_inicio: new Date().toISOString().split("T")[0],
    cid: "", cid_descricao: "", motivo_informado: "", salario_base: "",
  });

  const criar = useMutation({
    mutationFn: (data: any) => apiClient.post("/afastamentos/", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["afastamentos"] });
      qc.invalidateQueries({ queryKey: ["afastamentos-kpis"] });
      setShowModal(false);
      setForm({ trabalhador_id: "", tipo: "doenca", data_inicio: new Date().toISOString().split("T")[0], cid: "", cid_descricao: "", motivo_informado: "", salario_base: "" });
    },
  });

  const atualizar = useMutation({
    mutationFn: ({ id, data }: any) => apiClient.patch(`/afastamentos/${id}/`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["afastamentos"] });
      qc.invalidateQueries({ queryKey: ["afastamentos-kpis"] });
    },
  });

  const diasAfastado = (inicio: string) => {
    const diff = new Date().getTime() - new Date(inicio).getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Afastamentos</h1>
          <p className="text-sm text-gray-500 mt-1">Controle de afastamentos por doença, acidente e retorno ao trabalho</p>
        </div>
        <button onClick={() => setShowModal(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + Novo Afastamento
        </button>
      </div>

      {kpis && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            { label: "Total", value: kpis.total, color: "text-gray-700" },
            { label: "Ativos", value: kpis.ativos, color: "text-blue-600" },
            { label: "Pendentes", value: kpis.pendentes, color: "text-orange-600" },
            { label: "Retorno Próximo", value: kpis.retorno_proximo, color: "text-teal-600" },
            { label: "Custo Estimado", value: `R$ ${kpis.custo_total_estimado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`, color: "text-red-600" },
          ].map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {["", "recebido", "em_analise", "pendente", "em_beneficio", "em_analise_inss", "alta_inss", "limbo", "retorno_proximo", "encerrado"].map((s) => (
          <button key={s} onClick={() => setFiltroStatus(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${filtroStatus === s ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"}`}>
            {s === "" ? "Todos" : STATUS_LABELS[s]?.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Carregando...</div>
        ) : afastamentos.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nenhum afastamento registrado.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Trabalhador","Tipo","CID","Início","Dias","Retorno Previsto","Status","Custo Est.",""].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {afastamentos.map((a: any) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.trabalhador_nome}</td>
                  <td className="px-4 py-3 text-gray-600">{TIPO_LABELS[a.tipo] || a.tipo}</td>
                  <td className="px-4 py-3">
                    {a.cid ? <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">{a.cid}</span> : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{a.data_inicio}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold ${diasAfastado(a.data_inicio) > 15 ? "text-red-600" : "text-gray-700"}`}>{diasAfastado(a.data_inicio)}d</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {a.data_prevista_retorno || <span className="text-orange-500 text-xs">Sem previsão</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_LABELS[a.status]?.color || "bg-gray-100 text-gray-700"}`}>
                      {STATUS_LABELS[a.status]?.label || a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {a.custo_total_estimado ? <span className="text-red-600 font-medium">R$ {Number(a.custo_total_estimado).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</span> : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => { setDetalhe(a); setResultadoAtestado(null); }} className="text-blue-600 hover:text-blue-800 text-xs font-medium">Abrir</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Novo Afastamento</h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600">Trabalhador *</label>
                <select className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.trabalhador_id} onChange={e => setForm({ ...form, trabalhador_id: e.target.value })}>
                  <option value="">Selecione...</option>
                  {trabalhadores.map((t: any) => <option key={t.id} value={t.id}>{t.nome}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600">Tipo *</label>
                  <select className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.tipo} onChange={e => setForm({ ...form, tipo: e.target.value })}>
                    {Object.entries(TIPO_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Data Início *</label>
                  <input type="date" className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.data_inicio} onChange={e => setForm({ ...form, data_inicio: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600">CID-10</label>
                  <input type="text" placeholder="Ex: M54.5" className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.cid} onChange={e => setForm({ ...form, cid: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Salário Base (R$)</label>
                  <input type="number" placeholder="Ex: 3500.00" className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.salario_base} onChange={e => setForm({ ...form, salario_base: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Diagnóstico</label>
                <input type="text" placeholder="Ex: Lombalgia inespecífica" className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.cid_descricao} onChange={e => setForm({ ...form, cid_descricao: e.target.value })} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Motivo Informado</label>
                <textarea rows={2} className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.motivo_informado} onChange={e => setForm({ ...form, motivo_informado: e.target.value })} />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowModal(false)} className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50">Cancelar</button>
              <button onClick={() => criar.mutate({ ...form, salario_base: form.salario_base ? parseFloat(form.salario_base) : null })}
                disabled={!form.trabalhador_id || !form.data_inicio || criar.isPending}
                className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                {criar.isPending ? "Salvando..." : "Registrar Afastamento"}
              </button>
            </div>
          </div>
        </div>
      )}

      {detalhe && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-gray-900">Caso: {detalhe.trabalhador_nome}</h2>
              <button onClick={() => setDetalhe(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Tipo</p>
                  <p className="font-medium">{TIPO_LABELS[detalhe.tipo] || detalhe.tipo}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">CID</p>
                  <p className="font-medium font-mono">{detalhe.cid || "—"}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Início</p>
                  <p className="font-medium">{detalhe.data_inicio}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Dias afastado</p>
                  <p className={`font-bold ${diasAfastado(detalhe.data_inicio) > 15 ? "text-red-600" : "text-gray-900"}`}>
                    {diasAfastado(detalhe.data_inicio)} dias {diasAfastado(detalhe.data_inicio) > 15 && "⚠️ INSS"}
                  </p>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600">Atualizar Status</label>
                <select className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm" defaultValue={detalhe.status}
                  onChange={e => atualizar.mutate({ id: detalhe.id, data: { status: e.target.value } })}>
                  {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600">Data Prevista de Retorno</label>
                <input type="date" className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  defaultValue={detalhe.data_prevista_retorno || ""}
                  onBlur={e => { if (e.target.value) atualizar.mutate({ id: detalhe.id, data: { data_prevista_retorno: e.target.value } }) }} />
              </div>

              {/* Upload Atestado */}
              <div className="border-t border-gray-100 pt-3 mt-3">
                <p className="text-xs font-medium text-gray-600 mb-2">📎 Enviar Atestado Médico</p>
                <input ref={fileInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.txt" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) uploadAtestado(f, detalhe.id); }} />
                <button onClick={() => fileInputRef.current?.click()} disabled={uploadando}
                  className="w-full border-2 border-dashed border-gray-300 rounded-lg py-3 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors disabled:opacity-50">
                  {uploadando ? "⏳ Analisando com IA..." : "Clique para enviar PDF ou imagem"}
                </button>
                {resultadoAtestado && !resultadoAtestado.erro && (
                  <div className={`mt-3 rounded-lg p-3 text-xs ${resultadoAtestado.status === "valido" ? "bg-green-50 border border-green-200" : "bg-yellow-50 border border-yellow-200"}`}>
                    <div className="flex justify-between items-center mb-2">
                      <p className="font-bold">{resultadoAtestado.status === "valido" ? "✅ Atestado Válido" : "⚠️ Pendente Complemento"}</p>
                      <span className="font-bold text-blue-700">{Math.round((resultadoAtestado.score || 0) * 100)}% conformidade</span>
                    </div>
                    {resultadoAtestado.dados_extraidos?.cid && <p className="text-gray-600">CID {resultadoAtestado.dados_extraidos.cid} — {resultadoAtestado.dados_extraidos.diagnostico}</p>}
                    {resultadoAtestado.dados_extraidos?.prazo_dias && <p className="text-gray-600">{resultadoAtestado.dados_extraidos.prazo_dias} dias — {resultadoAtestado.dados_extraidos.medico_nome}</p>}
                    {resultadoAtestado.alertas?.slice(0,2).map((a: string, i: number) => <p key={i} className="text-yellow-700 mt-1">⚠️ {a}</p>)}
                  </div>
                )}
              </div>

              {detalhe.historico?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-600 mb-2">Histórico</p>
                  <div className="space-y-2">
                    {detalhe.historico.map((h: any, i: number) => (
                      <div key={i} className="flex gap-2 text-xs text-gray-600 border-l-2 border-blue-200 pl-2">
                        <span className="text-gray-400">{new Date(h.data).toLocaleString("pt-BR")}</span>
                        <span>{h.acao}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {diasAfastado(detalhe.data_inicio) >= 15 && detalhe.status !== "encerrado" && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-xs font-bold text-red-700">⚠️ Afastamento superior a 15 dias</p>
                  <p className="text-xs text-red-600 mt-1">A partir do 16º dia, o ônus passa para o INSS.</p>
                </div>
              )}
              {detalhe.status === "limbo" && (
                <div className="bg-red-50 border-2 border-red-500 rounded-lg p-3">
                  <p className="text-xs font-bold text-red-800">🚨 LIMBO — Via Judicial</p>
                  <p className="text-xs text-red-700 mt-1">INSS negou o benefício. Acionar advogado previdenciário. Prazo recurso: 30 dias.</p>
                </div>
              )}
              {detalhe.status === "alta_inss" && (
                <div className="bg-indigo-50 border border-indigo-300 rounded-lg p-3">
                  <p className="text-xs font-bold text-indigo-800">🏥 Alta do INSS — Retorno Pendente</p>
                  <p className="text-xs text-indigo-700 mt-1">Agendar avaliação com médico do trabalho antes do retorno.</p>
                </div>
              )}
              {detalhe.status === "em_beneficio" && (
                <div className="bg-green-50 border border-green-300 rounded-lg p-3">
                  <p className="text-xs font-bold text-green-800">✅ Benefício INSS Ativo</p>
                  <p className="text-xs text-green-700 mt-1">Monitorar vencimento e prorrogação (15 dias antes do vencimento).</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
