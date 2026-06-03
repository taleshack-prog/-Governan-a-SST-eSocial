import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, CheckCircle, Clock, Calendar, AlertCircle, Upload, MessageCircle, X } from "lucide-react";
import { api } from "../api/client";

const STATUS_INFO: Record<string, { label: string; color: string; bg: string }> = {
  recebido:        { label: "Recebido",            color: "#1a9e8f", bg: "#e6f7f5" },
  em_analise:      { label: "Em análise",          color: "#f59e0b", bg: "#fef3c7" },
  em_beneficio:    { label: "Em benefício INSS",   color: "#10b981", bg: "#d1fae5" },
  em_analise_inss: { label: "Em análise INSS",     color: "#f59e0b", bg: "#fef3c7" },
  alta_inss:       { label: "Alta do INSS",        color: "#6366f1", bg: "#ede9fe" },
  limbo:           { label: "Via Judicial",        color: "#ef4444", bg: "#fee2e2" },
  retorno_proximo: { label: "Retorno próximo",     color: "#0f2744", bg: "#dbeafe" },
  encerrado:       { label: "Encerrado",           color: "#6b7280", bg: "#f3f4f6" },
};

export default function MeuAfastamento() {

  const qc = useQueryClient();
  const [showComunicar, setShowComunicar] = useState(false);
  const [showAtestado, setShowAtestado] = useState(false);
  const [showMensagem, setShowMensagem] = useState(false);
  const [uploadando, setUploadando] = useState(false);
  const [resultadoUpload, setResultadoUpload] = useState<any>(null);
  const [mensagem, setMensagem] = useState("");
  const [ausenciaForm, setAusenciaForm] = useState({ motivo: "", data_inicio: "", cid: "" });
  const [enviando, setEnviando] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: afastamentos = [] } = useQuery({
    queryKey: ["meus-afastamentos"],
    queryFn: async () => {
      const token = localStorage.getItem("radar_func_token");
      const resp = await api.get("/funcionarios/auth/meus-afastamentos", {
        headers: { Authorization: `Bearer ${token}` }
      });
      return resp.data;
    },
  });

  const afastamento = afastamentos[0];
  const status = afastamento ? STATUS_INFO[afastamento.status] || { label: afastamento.status, color: "#6b7280", bg: "#f3f4f6" } : null;

  const diasAfastado = (inicio: string) => {
    const diff = new Date().getTime() - new Date(inicio).getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  };

  const uploadAtestado = async (file: File) => {
    if (!afastamento) return;
    setUploadando(true);
    setResultadoUpload(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const token = localStorage.getItem("radar_func_token");
      const resp = await api.post(`/funcionarios/auth/enviar-atestado/${afastamento.id}`, fd, {
        headers: { 
          "Content-Type": "multipart/form-data",
          "Authorization": `Bearer ${token}`
        }
      });
      setResultadoUpload(resp.data);
      qc.invalidateQueries({ queryKey: ["meus-afastamentos"] });
    } catch {
      setResultadoUpload({ erro: "Erro ao enviar. Tente novamente." });
    } finally {
      setUploadando(false);
    }
  };

  const comunicarAusencia = async () => {
    setEnviando(true);
    try {
      await api.post("/afastamentos/", {
        trabalhador_id: afastamento?.trabalhador_id,
        tipo: "doenca",
        data_inicio: ausenciaForm.data_inicio || new Date().toISOString().split("T")[0],
        cid: ausenciaForm.cid,
        motivo_informado: ausenciaForm.motivo,
      });
      qc.invalidateQueries({ queryKey: ["meus-afastamentos"] });
      setShowComunicar(false);
    } catch {
      alert("Erro ao comunicar ausência. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  };

  const passos = [
    { label: "Documento enviado", feito: afastamento?.num_atestados > 0 },
    { label: "RH analisando", feito: afastamento?.status !== "recebido", ativo: afastamento?.status === "em_analise" },
    { label: "Confirmação de retorno", feito: afastamento?.status === "encerrado" },
  ];

  return (
    <div className="min-h-screen bg-[#f5f6fa] pb-24">
      {/* Header */}
      <div className="bg-[#0f2744] text-white px-5 pt-12 pb-6 safe-top">
        <h1 className="text-2xl font-bold">Meu afastamento</h1>
        <p className="text-blue-300 text-sm mt-0.5">Envie documentos e acompanhe seu retorno</p>
      </div>

      <div className="px-4 -mt-2 space-y-4">
        {/* Card do funcionário */}
        {afastamento ? (
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg"
                style={{ backgroundColor: "#1a9e8f" }}>
                {afastamento.trabalhador_nome?.split(" ").map((n: string) => n[0]).slice(0, 2).join("")}
              </div>
              <div className="flex-1">
                <p className="font-bold text-gray-900">{afastamento.trabalhador_nome}</p>
                <p className="text-xs text-gray-500">{afastamento.cid_descricao || afastamento.cid || "Afastamento registrado"}</p>
              </div>
              <span className="text-xs font-medium px-3 py-1.5 rounded-full border"
                style={{ color: status?.color, backgroundColor: status?.bg, borderColor: status?.color + "30" }}>
                {status?.label}
              </span>
            </div>
            <div className="flex gap-4 mt-3 pt-3 border-t border-gray-100">
              <div className="text-center">
                <p className="text-xs text-gray-500">Dias afastado</p>
                <p className="font-bold text-[#0f2744]">{diasAfastado(afastamento.data_inicio)}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500">CID</p>
                <p className="font-bold text-[#0f2744]">{afastamento.cid || "—"}</p>
              </div>
              {afastamento.data_prevista_retorno && (
                <div className="text-center">
                  <p className="text-xs text-gray-500">Retorno previsto</p>
                  <p className="font-bold text-[#1a9e8f]">{new Date(afastamento.data_prevista_retorno).toLocaleDateString("pt-BR")}</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl p-4 shadow-sm text-center">
            <p className="text-gray-500 text-sm">Nenhum afastamento ativo.</p>
          </div>
        )}

        {/* Ações */}
        <div className="space-y-3">
          <button onClick={() => setShowComunicar(true)}
            className="w-full bg-white rounded-2xl p-4 shadow-sm flex items-center gap-4 active:scale-95 transition-transform">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ backgroundColor: "#e6f7f5" }}>
              <Calendar size={22} color="#1a9e8f" />
            </div>
            <div className="flex-1 text-left">
              <p className="font-semibold text-gray-900">Comunicar ausência</p>
              <p className="text-xs text-gray-500">Informe sua ausência à empresa</p>
            </div>
            <ChevronRight size={18} color="#9ca3af" />
          </button>

          <button onClick={() => setShowAtestado(true)}
            className="w-full bg-white rounded-2xl p-4 shadow-sm flex items-center gap-4 active:scale-95 transition-transform">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ backgroundColor: "#dbeafe" }}>
              <Upload size={22} color="#3b82f6" />
            </div>
            <div className="flex-1 text-left">
              <p className="font-semibold text-gray-900">Enviar atestado</p>
              <p className="text-xs text-gray-500">Envie seu atestado médico</p>
            </div>
            <ChevronRight size={18} color="#9ca3af" />
          </button>

          <button onClick={() => setShowMensagem(true)}
            className="w-full bg-white rounded-2xl p-4 shadow-sm flex items-center gap-4 active:scale-95 transition-transform">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ backgroundColor: "#ede9fe" }}>
              <MessageCircle size={22} color="#6366f1" />
            </div>
            <div className="flex-1 text-left">
              <p className="font-semibold text-gray-900">Falar com RH</p>
              <p className="text-xs text-gray-500">Tire dúvidas ou solicite suporte</p>
            </div>
            <ChevronRight size={18} color="#9ca3af" />
          </button>
        </div>

        {/* Meu status */}
        {afastamento && (
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <h2 className="font-bold text-gray-900 mb-3">Meu status</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <CheckCircle size={20} color={afastamento.num_atestados > 0 ? "#10b981" : "#d1d5db"} />
                <p className="text-sm text-gray-700">
                  Atestado {afastamento.num_atestados > 0 ? <span className="text-green-600 font-medium">recebido</span> : <span className="text-gray-400">não enviado</span>}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Clock size={20} color="#f59e0b" />
                <p className="text-sm text-gray-700">
                  Status da análise: <span className="font-medium" style={{ color: status?.color }}>{status?.label}</span>
                </p>
              </div>
              {afastamento.data_prevista_retorno && (
                <div className="flex items-center gap-3">
                  <Calendar size={20} color="#1a9e8f" />
                  <p className="text-sm text-gray-700">
                    Retorno previsto: <span className="text-[#1a9e8f] font-medium">
                      {new Date(afastamento.data_prevista_retorno).toLocaleDateString("pt-BR")}
                    </span>
                  </p>
                </div>
              )}
              <div className="flex items-center gap-3">
                <CheckCircle size={20} color="#10b981" />
                <p className="text-sm text-gray-700">Pendências: <span className="text-green-600 font-medium">nenhuma</span></p>
              </div>
            </div>
          </div>
        )}

        {/* Próximos passos */}
        {afastamento && (
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <h2 className="font-bold text-gray-900 mb-4">Próximos passos</h2>
            <div className="space-y-4">
              {passos.map((p, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
                    p.feito ? "bg-[#1a9e8f] text-white" :
                    p.ativo ? "bg-[#0f2744] text-white" :
                    "bg-gray-200 text-gray-400"
                  }`}>
                    {p.feito ? "✓" : i + 1}
                  </div>
                  <p className={`text-sm ${p.feito ? "text-gray-400 line-through" : p.ativo ? "text-gray-900 font-medium" : "text-gray-400"}`}>
                    {p.label}
                  </p>
                  <div className="ml-auto">
                    {p.feito ? <CheckCircle size={16} color="#1a9e8f" /> :
                     p.ativo ? <Clock size={16} color="#0f2744" /> :
                     <div className="w-4 h-4 rounded-full border-2 border-gray-300" />}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modal Comunicar Ausência */}
      {showComunicar && (
        <div className="fixed inset-0 bg-black/60 flex items-end z-50">
          <div className="bg-white w-full rounded-t-3xl p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-gray-900 text-lg">Comunicar ausência</h3>
              <button onClick={() => setShowComunicar(false)}><X size={20} color="#6b7280" /></button>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Data de início</label>
              <input type="date" className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm"
                value={ausenciaForm.data_inicio} onChange={e => setAusenciaForm({...ausenciaForm, data_inicio: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">CID (se souber)</label>
              <input type="text" placeholder="Ex: M54.5" className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm"
                value={ausenciaForm.cid} onChange={e => setAusenciaForm({...ausenciaForm, cid: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Motivo</label>
              <textarea rows={3} placeholder="Descreva brevemente o motivo da ausência"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none"
                value={ausenciaForm.motivo} onChange={e => setAusenciaForm({...ausenciaForm, motivo: e.target.value})} />
            </div>
            <button onClick={comunicarAusencia} disabled={enviando || !ausenciaForm.data_inicio}
              className="w-full bg-[#0f2744] text-white rounded-xl py-4 font-semibold text-sm disabled:opacity-50">
              {enviando ? "Enviando..." : "Comunicar ausência"}
            </button>
          </div>
        </div>
      )}

      {/* Modal Enviar Atestado */}
      {showAtestado && (
        <div className="fixed inset-0 bg-black/60 flex items-end z-50">
          <div className="bg-white w-full rounded-t-3xl p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-gray-900 text-lg">Enviar atestado</h3>
              <button onClick={() => setShowAtestado(false)}><X size={20} color="#6b7280" /></button>
            </div>
            <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) uploadAtestado(f); }} />
            <button onClick={() => fileRef.current?.click()} disabled={uploadando || !afastamento}
              className="w-full border-2 border-dashed border-[#1a9e8f] rounded-2xl py-8 flex flex-col items-center gap-2 disabled:opacity-50">
              <Upload size={32} color="#1a9e8f" />
              <p className="text-sm font-medium text-[#1a9e8f]">
                {uploadando ? "Analisando com IA..." : "Toque para selecionar o arquivo"}
              </p>
              <p className="text-xs text-gray-400">PDF, JPG ou PNG</p>
            </button>
            {resultadoUpload && (
              <div className={`rounded-xl p-4 ${resultadoUpload.erro ? "bg-red-50" : resultadoUpload.status === "valido" ? "bg-green-50" : "bg-yellow-50"}`}>
                {resultadoUpload.erro ? (
                  <p className="text-sm text-red-600">{resultadoUpload.erro}</p>
                ) : (
                  <>
                    <p className="font-semibold text-sm mb-1">
                      {resultadoUpload.status === "valido" ? "✅ Atestado válido!" : "⚠️ Verificar atestado"}
                    </p>
                    <p className="text-xs text-gray-600">
                      Conformidade: {Math.round((resultadoUpload.score || 0) * 100)}%
                    </p>
                    {resultadoUpload.alertas?.slice(0, 2).map((a: string, i: number) => (
                      <p key={i} className="text-xs text-orange-600 mt-1">• {a}</p>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal Falar com RH */}
      {showMensagem && (
        <div className="fixed inset-0 bg-black/60 flex items-end z-50">
          <div className="bg-white w-full rounded-t-3xl p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-gray-900 text-lg">Falar com RH</h3>
              <button onClick={() => setShowMensagem(false)}><X size={20} color="#6b7280" /></button>
            </div>
            <textarea rows={4} placeholder="Digite sua mensagem para o RH..."
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none"
              value={mensagem} onChange={e => setMensagem(e.target.value)} />
            <button disabled={!mensagem}
              className="w-full bg-[#6366f1] text-white rounded-xl py-4 font-semibold text-sm disabled:opacity-50">
              Enviar mensagem
            </button>
            <p className="text-xs text-gray-400 text-center">O RH responderá em até 24 horas úteis</p>
          </div>
        </div>
      )}
    </div>
  );
}
