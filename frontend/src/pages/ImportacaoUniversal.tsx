import { useState, useRef, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { SectionTitle } from "../components/ui";
import { CheckCircle, AlertTriangle, FileText, FileSpreadsheet, File } from "lucide-react";

const TIPO_CONFIG: Record<string, { cor: string; label: string; icone: string }> = {
  LTCAT:        { cor: "text-blue-700",   label: "LTCAT",           icone: "📋" },
  PPP:          { cor: "text-purple-700", label: "PPP",             icone: "📄" },
  ATESTADO:     { cor: "text-green-700",  label: "Atestado",        icone: "🏥" },
  TRABALHADORES:{ cor: "text-teal-700",   label: "Trabalhadores",   icone: "👥" },
  AFASTAMENTOS: { cor: "text-amber-700",  label: "Afastamentos",    icone: "📅" },
  CAT:          { cor: "text-red-700",    label: "CAT",             icone: "🚨" },
  PCMSO:        { cor: "text-indigo-700", label: "PCMSO",           icone: "⚕️" },
  OUTRO:        { cor: "text-gray-700",   label: "Outro",           icone: "📎" },
};

export default function ImportacaoUniversal() {
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [etapa, setEtapa] = useState<"upload"|"processando"|"resultado">("upload");
  const [jobId, setJobId] = useState<string|null>(null);
  const [resultado, setResultado] = useState<any>(null);
  const [arquivo, setArquivo] = useState<string>("");
  const [erro, setErro] = useState<string|null>(null);

  const enviar = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("arquivo", file);
      return apiClient.post("/importacao-universal/analisar", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      }).then(r => r.data);
    },
    onSuccess: (data) => { setJobId(data.job_id); setArquivo(data.arquivo); setEtapa("processando"); },
    onError: () => setErro("Erro ao enviar arquivo."),
  });

  useEffect(() => {
    if (!jobId || etapa !== "processando") return;
    const interval = setInterval(async () => {
      try {
        const s = await apiClient.get(`/importacao-universal/status/${jobId}`).then(r => r.data);
        if (s.status === "concluido") {
          clearInterval(interval);
          setResultado(s);
          setEtapa("resultado");
          ["trabalhadores","documentos","agentes","inconsistencias"].forEach(k =>
            queryClient.invalidateQueries({ queryKey: [k] }));
        } else if (s.status === "erro") {
          clearInterval(interval);
          setErro(s.erro || "Erro ao processar.");
          setEtapa("upload");
        }
      } catch {}
    }, 5000);
    return () => clearInterval(interval);
  }, [jobId, etapa]);

  const handleFile = (file: File) => { setErro(null); enviar.mutate(file); };
  const tipo = resultado?.tipo_documento || "OUTRO";
  const cfg = TIPO_CONFIG[tipo] || TIPO_CONFIG.OUTRO;

  return (
    <div className="space-y-6 max-w-3xl">
      <SectionTitle title="Importação Universal" subtitle="Envie qualquer documento — a IA detecta o tipo e posiciona os dados automaticamente" />

      <div className="grid grid-cols-4 gap-2">
        {Object.entries(TIPO_CONFIG).filter(([k]) => k !== "OUTRO").map(([t, c]) => (
          <div key={t} className="bg-white rounded-xl p-3 border border-gray-100 text-center">
            <div className="text-xl mb-1">{c.icone}</div>
            <div className={`text-xs font-semibold ${c.cor}`}>{c.label}</div>
          </div>
        ))}
      </div>

      {etapa === "upload" && (
        <div className="space-y-4">
          <div onClick={() => inputRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if(f) handleFile(f); }}
            className="border-2 border-dashed border-gray-200 rounded-2xl p-12 text-center cursor-pointer hover:border-[#1a9e8f] hover:bg-teal-50/30 transition-all">
            <input ref={inputRef} type="file" accept=".pdf,.xlsx,.xls,.csv,.xml" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if(f) handleFile(f); }} />
            {enviar.isPending ? (
              <div className="space-y-3">
                <div className="w-12 h-12 border-4 border-[#1a9e8f] border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm font-medium text-gray-600">Enviando...</p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex justify-center gap-3">
                  <FileText size={32} className="text-gray-300" />
                  <FileSpreadsheet size={32} className="text-gray-300" />
                  <File size={32} className="text-gray-300" />
                </div>
                <p className="font-semibold text-gray-700">Arraste ou clique para selecionar</p>
                <p className="text-sm text-gray-400">PDF, Excel, CSV ou XML · Máximo 25MB</p>
                <p className="text-xs text-gray-400">A IA detecta: LTCAT, PPP, Atestado, Trabalhadores, Afastamentos, CAT, PCMSO</p>
              </div>
            )}
          </div>
          {erro && <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">{erro}</div>}
        </div>
      )}

      {etapa === "processando" && (
        <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm text-center space-y-4">
          <div className="w-16 h-16 border-4 border-[#1a9e8f] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="font-bold text-gray-900">IA analisando {arquivo}...</p>
          <p className="text-sm text-gray-500">Detectando tipo e extraindo dados automaticamente</p>
        </div>
      )}

      {etapa === "resultado" && resultado && (
        <div className="space-y-4">
          <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center">
            <CheckCircle size={40} className="mx-auto text-green-500 mb-3" />
            <p className="font-bold text-lg text-gray-900">Documento importado!</p>
            <div className="flex items-center justify-center gap-2 mt-2">
              <span className="text-2xl">{cfg.icone}</span>
              <span className={`font-bold ${cfg.cor}`}>{cfg.label}</span>
              <span className="text-xs text-gray-400">({Math.round((resultado.confianca||0)*100)}% confiança)</span>
            </div>
            {resultado.resumo && <p className="text-sm text-gray-600 mt-2">{resultado.resumo}</p>}
          </div>

          <div className="grid grid-cols-3 gap-3">
            {resultado.agentes_criados > 0 && (
              <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
                <p className="text-2xl font-bold text-blue-600">{resultado.agentes_criados}</p>
                <p className="text-xs text-gray-500 mt-1">Agentes nocivos</p>
              </div>
            )}
            {resultado.trabalhadores_importados > 0 && (
              <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
                <p className="text-2xl font-bold text-teal-600">{resultado.trabalhadores_importados}</p>
                <p className="text-xs text-gray-500 mt-1">Trabalhadores</p>
              </div>
            )}
            {resultado.duplicados > 0 && (
              <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
                <p className="text-2xl font-bold text-amber-500">{resultado.duplicados}</p>
                <p className="text-xs text-gray-500 mt-1">Duplicados</p>
              </div>
            )}
          </div>

          <button onClick={() => { setEtapa("upload"); setResultado(null); setJobId(null); setErro(null); }}
            className="w-full border border-gray-200 text-gray-600 rounded-xl py-3 text-sm font-semibold hover:bg-gray-50">
            Importar outro documento
          </button>
        </div>
      )}
    </div>
  );
}
