import { useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { SectionTitle } from "../components/ui";
import { Upload, CheckCircle, AlertTriangle, FileSpreadsheet, ArrowRight, Shield } from "lucide-react";

const CAMPOS_PT: Record<string, string> = {
  nome: "Nome", cpf: "CPF", data_nascimento: "Data Nasc.",
  sexo: "Sexo", pis_pasep: "PIS/PASEP", cargo: "Cargo",
  setor: "Setor", matricula: "Matrícula", data_admissao: "Admissão",
  ctps_numero: "CTPS Nº", ctps_serie: "CTPS Série", ctps_uf: "CTPS UF", ges: "GES",
};

const SENSIVEIS_PADRAO = ["cpf", "pis_pasep", "ctps_numero", "data_nascimento"];

export default function Importacao() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [etapa, setEtapa] = useState<"upload"|"preview"|"resultado">("upload");
  const [analise, setAnalise] = useState<any>(null);
  const [resultado, setResultado] = useState<any>(null);
  const [sensiveis, setSensiveis] = useState<string[]>(SENSIVEIS_PADRAO);
  const [sobrescrever, setSobrescrever] = useState(false);
  const [arquivo, setArquivo] = useState<File | null>(null);

  const analisar = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("arquivo", file);
      fd.append("campos_sensiveis", sensiveis.join(","));
      return apiClient.post("/importacao/analisar", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      }).then(r => r.data);
    },
    onSuccess: (data) => { setAnalise(data); setEtapa("preview"); },
  });

  const confirmar = useMutation({
    mutationFn: async () => {
      return apiClient.post("/importacao/confirmar", {
        session_id: analise.session_id,
        mapeamento: analise.mapeamento,
        campos_sensiveis: sensiveis,
        sobrescrever_existentes: sobrescrever,
      }).then(r => r.data);
    },
    onSuccess: (data) => {
      setResultado(data);
      setEtapa("resultado");
      queryClient.invalidateQueries({ queryKey: ["trabalhadores"] });
      queryClient.invalidateQueries({ queryKey: ["radar-score"] });
      queryClient.invalidateQueries({ queryKey: ["inconsistencias"] });
    },
  });

  const handleFile = (file: File) => {
    setArquivo(file);
    analisar.mutate(file);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <SectionTitle title="Importação Inteligente" subtitle="Importe trabalhadores de planilha Excel ou CSV com mapeamento automático por IA" />

      {/* Etapas */}
      <div className="flex items-center gap-2 text-xs font-semibold">
        {["Upload", "Revisar", "Resultado"].map((e, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs
              ${i === ["upload","preview","resultado"].indexOf(etapa) ? "bg-[#0f2744] text-white" : "bg-gray-100 text-gray-400"}`}>
              {i + 1}
            </div>
            <span className={i === ["upload","preview","resultado"].indexOf(etapa) ? "text-[#0f2744]" : "text-gray-400"}>{e}</span>
            {i < 2 && <ArrowRight size={12} className="text-gray-300" />}
          </div>
        ))}
      </div>

      {/* ETAPA 1 — UPLOAD */}
      {etapa === "upload" && (
        <div className="space-y-4">
          {/* Campos sensíveis */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <Shield size={16} className="text-[#1a9e8f]" />
              <p className="font-semibold text-sm text-gray-900">Campos sensíveis — não serão importados</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(CAMPOS_PT).map(([campo, label]) => (
                <button key={campo} onClick={() => setSensiveis(prev =>
                  prev.includes(campo) ? prev.filter(s => s !== campo) : [...prev, campo]
                )}
                  className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${
                    sensiveis.includes(campo)
                      ? "bg-red-50 border-red-200 text-red-700"
                      : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                  }`}>
                  {sensiveis.includes(campo) ? "🔒 " : ""}{label}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">Clique para marcar/desmarcar campos sensíveis</p>
          </div>

          {/* Drop zone */}
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
            className="border-2 border-dashed border-gray-200 rounded-2xl p-12 text-center cursor-pointer hover:border-[#1a9e8f] hover:bg-teal-50/30 transition-all">
            <input ref={inputRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
            {analisar.isPending ? (
              <div className="space-y-3">
                <div className="w-12 h-12 border-4 border-[#1a9e8f] border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm font-medium text-gray-600">IA mapeando colunas...</p>
              </div>
            ) : (
              <div className="space-y-3">
                <FileSpreadsheet size={40} className="mx-auto text-gray-300" />
                <p className="font-semibold text-gray-700">Arraste ou clique para selecionar</p>
                <p className="text-sm text-gray-400">Excel (.xlsx, .xls) ou CSV · Até 15.000 linhas</p>
              </div>
            )}
          </div>
          {analisar.isError && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
              Erro ao analisar arquivo. Verifique o formato e tente novamente.
            </div>
          )}
        </div>
      )}

      {/* ETAPA 2 — PREVIEW */}
      {etapa === "preview" && analise && (
        <div className="space-y-4">
          {/* Resumo */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
              <p className="text-2xl font-bold text-[#0f2744]">{analise.total_linhas}</p>
              <p className="text-xs text-gray-500 mt-1">Registros encontrados</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
              <p className="text-2xl font-bold text-teal-600">{Object.keys(analise.campos_mapeados).length}</p>
              <p className="text-xs text-gray-500 mt-1">Colunas mapeadas pela IA</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
              <p className="text-2xl font-bold text-red-500">{sensiveis.length}</p>
              <p className="text-xs text-gray-500 mt-1">Campos protegidos</p>
            </div>
          </div>

          {/* Mapeamento */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
            <p className="font-semibold text-sm text-gray-900 mb-3">Mapeamento detectado pela IA</p>
            <div className="space-y-2">
              {Object.entries(analise.campos_mapeados).map(([col, campo]: any) => (
                <div key={col} className="flex items-center gap-3 text-xs">
                  <span className="bg-gray-100 px-2 py-1 rounded font-mono text-gray-600 min-w-40">{col}</span>
                  <ArrowRight size={12} className="text-gray-400 flex-shrink-0" />
                  <span className={`px-2 py-1 rounded font-semibold ${
                    sensiveis.includes(campo) ? "bg-red-50 text-red-700" : "bg-teal-50 text-teal-700"
                  }`}>
                    {sensiveis.includes(campo) ? "🔒 " : ""}{CAMPOS_PT[campo] || campo}
                  </span>
                  {sensiveis.includes(campo) && <span className="text-gray-400">— não importado</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Preview de dados */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm overflow-x-auto">
            <p className="font-semibold text-sm text-gray-900 mb-3">Preview — primeiros 5 registros</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100">
                  {Object.keys(analise.preview[0] || {}).map(k => (
                    <th key={k} className="text-left py-2 pr-4 text-gray-500 font-semibold">{CAMPOS_PT[k] || k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {analise.preview.map((row: any, i: number) => (
                  <tr key={i} className="border-b border-gray-50">
                    {Object.values(row).map((v: any, j: number) => (
                      <td key={j} className={`py-2 pr-4 ${String(v).includes("***") ? "text-red-400 italic" : "text-gray-700"}`}>
                        {String(v) || "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Opções */}
          <div className="flex items-center gap-3">
            <input type="checkbox" id="sobrescrever" checked={sobrescrever}
              onChange={e => setSobrescrever(e.target.checked)} className="rounded" />
            <label htmlFor="sobrescrever" className="text-sm text-gray-600">
              Sobrescrever trabalhadores com CPF duplicado
            </label>
          </div>

          {/* Ações */}
          <div className="flex gap-3">
            <button onClick={() => { setEtapa("upload"); setAnalise(null); }}
              className="flex-1 border border-gray-200 text-gray-600 rounded-xl py-3 text-sm font-semibold hover:bg-gray-50">
              Voltar
            </button>
            <button onClick={() => confirmar.mutate()}
              disabled={confirmar.isPending}
              className="flex-1 bg-[#0f2744] text-white rounded-xl py-3 text-sm font-semibold hover:bg-[#1a9e8f] disabled:opacity-50 transition-colors">
              {confirmar.isPending ? "Importando..." : `Importar ${analise.total_linhas} registros →`}
            </button>
          </div>
        </div>
      )}

      {/* ETAPA 3 — RESULTADO */}
      {etapa === "resultado" && resultado && (
        <div className="space-y-4">
          <div className={`rounded-2xl p-6 border text-center ${resultado.sucesso ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
            {resultado.sucesso
              ? <CheckCircle size={40} className="mx-auto text-green-500 mb-3" />
              : <AlertTriangle size={40} className="mx-auto text-red-500 mb-3" />}
            <p className="font-bold text-lg text-gray-900">{resultado.mensagem}</p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
              <p className="text-2xl font-bold text-green-600">{resultado.importados}</p>
              <p className="text-xs text-gray-500 mt-1">Importados</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
              <p className="text-2xl font-bold text-amber-500">{resultado.duplicados}</p>
              <p className="text-xs text-gray-500 mt-1">Duplicados ignorados</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
              <p className="text-2xl font-bold text-red-500">{resultado.total_erros}</p>
              <p className="text-xs text-gray-500 mt-1">Erros</p>
            </div>
          </div>

          {resultado.erros?.length > 0 && (
            <div className="bg-white rounded-2xl p-5 border border-red-100">
              <p className="font-semibold text-sm text-red-700 mb-3">Erros de importação</p>
              {resultado.erros.map((e: any, i: number) => (
                <div key={i} className="text-xs text-red-600 mb-1">Linha {e.linha}: {e.erro}</div>
              ))}
            </div>
          )}

          <button onClick={() => { setEtapa("upload"); setAnalise(null); setResultado(null); setArquivo(null); }}
            className="w-full border border-gray-200 text-gray-600 rounded-xl py-3 text-sm font-semibold hover:bg-gray-50">
            Nova importação
          </button>
        </div>
      )}
    </div>
  );
}
