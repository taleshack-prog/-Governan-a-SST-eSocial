import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { SectionTitle } from "../components/ui";
import { FileText, CheckCircle, AlertTriangle, ArrowRight, Shield } from "lucide-react";

export default function ImportacaoPDF() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [etapa, setEtapa] = useState<"upload"|"preview"|"resultado">("upload");
  const [analise, setAnalise] = useState<any>(null);
  const [resultado, setResultado] = useState<any>(null);
  const [arquivo, setArquivo] = useState<File|null>(null);

  const analisar = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("arquivo", file);
      return apiClient.post("/importacao/ltcat/analisar", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      }).then(r => r.data);
    },
    onSuccess: (data) => { setAnalise(data); setEtapa("preview"); },
  });

  const confirmar = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("arquivo", arquivo!);
      return apiClient.post("/importacao/ltcat/confirmar", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      }).then(r => r.data);
    },
    onSuccess: (data) => { setResultado(data); setEtapa("resultado"); },
  });

  const handleFile = (file: File) => {
    setArquivo(file);
    analisar.mutate(file);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <SectionTitle title="Importar LTCAT" subtitle="Importe o Laudo Técnico das Condições Ambientais com extração automática de agentes nocivos por IA" />

      {/* Etapas */}
      <div className="flex items-center gap-2 text-xs font-semibold">
        {["Upload PDF", "Revisar extração", "Resultado"].map((e, i) => (
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
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-700">
            <strong>O que a IA extrai do LTCAT:</strong> agentes nocivos, setores/GES, responsável técnico, datas de emissão e validade, níveis de exposição, EPC/EPI.
          </div>

          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if(f) handleFile(f); }}
            className="border-2 border-dashed border-gray-200 rounded-2xl p-12 text-center cursor-pointer hover:border-[#1a9e8f] hover:bg-teal-50/30 transition-all">
            <input ref={inputRef} type="file" accept=".pdf" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if(f) handleFile(f); }} />
            {analisar.isPending ? (
              <div className="space-y-3">
                <div className="w-12 h-12 border-4 border-[#1a9e8f] border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm font-medium text-gray-600">IA lendo e analisando o LTCAT...</p>
                <p className="text-xs text-gray-400">Isso pode levar até 30 segundos</p>
              </div>
            ) : (
              <div className="space-y-3">
                <FileText size={40} className="mx-auto text-gray-300" />
                <p className="font-semibold text-gray-700">Arraste ou clique para selecionar o PDF</p>
                <p className="text-sm text-gray-400">LTCAT em PDF · Máximo 20MB</p>
              </div>
            )}
          </div>
          {analisar.isError && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
              Erro ao analisar PDF. Verifique se o arquivo é um LTCAT em PDF com texto extraível.
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
              <p className="text-2xl font-bold text-[#0f2744]">{analise.total_agentes}</p>
              <p className="text-xs text-gray-500 mt-1">Agentes nocivos encontrados</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
              <p className="text-2xl font-bold text-teal-600">{analise.setores_encontrados?.length || 0}</p>
              <p className="text-xs text-gray-500 mt-1">Setores/GES identificados</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
              <p className="text-2xl font-bold text-amber-500">{analise.setores_empresa?.length || 0}</p>
              <p className="text-xs text-gray-500 mt-1">Setores na empresa</p>
            </div>
          </div>

          {/* Dados extraídos */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
            <p className="font-semibold text-sm text-gray-900 mb-3">Dados extraídos pela IA</p>
            <div className="space-y-2 text-sm">
              <div className="flex gap-2"><span className="text-gray-400 w-36 flex-shrink-0">Título:</span><span className="text-gray-700 font-medium">{analise.dados_extraidos?.titulo || "—"}</span></div>
              <div className="flex gap-2"><span className="text-gray-400 w-36 flex-shrink-0">Empresa:</span><span className="text-gray-700">{analise.dados_extraidos?.empresa || "—"}</span></div>
              <div className="flex gap-2"><span className="text-gray-400 w-36 flex-shrink-0">Data emissão:</span><span className="text-gray-700">{analise.dados_extraidos?.data_emissao || "—"}</span></div>
              <div className="flex gap-2"><span className="text-gray-400 w-36 flex-shrink-0">Validade:</span><span className="text-gray-700">{analise.dados_extraidos?.data_validade || "Não informado"}</span></div>
              <div className="flex gap-2"><span className="text-gray-400 w-36 flex-shrink-0">Responsável:</span><span className="text-gray-700">{analise.dados_extraidos?.responsavel_tecnico?.nome || "—"}</span></div>
            </div>
          </div>

          {/* Agentes nocivos */}
          {analise.preview_agentes?.length > 0 && (
            <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
              <p className="font-semibold text-sm text-gray-900 mb-3">
                Agentes nocivos extraídos {analise.total_agentes > 5 ? `(mostrando 5 de ${analise.total_agentes})` : ""}
              </p>
              <div className="space-y-2">
                {analise.preview_agentes.map((ag: any, i: number) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
                    <span className="text-xs font-mono bg-[#0f2744] text-white px-2 py-1 rounded flex-shrink-0">{ag.codigo_tabela24 || "—"}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{ag.descricao}</p>
                      <p className="text-xs text-gray-500 mt-0.5">Setor: {ag.setor || "—"} · Nível: {ag.nivel_exposicao || "—"}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-700 flex items-start gap-2">
            <Shield size={14} className="flex-shrink-0 mt-0.5" />
            <span>Dados extraídos por IA — recomendamos revisão técnica antes do envio ao eSocial. Todos os agentes serão marcados como "requer revisão".</span>
          </div>

          <div className="flex gap-3">
            <button onClick={() => { setEtapa("upload"); setAnalise(null); }}
              className="flex-1 border border-gray-200 text-gray-600 rounded-xl py-3 text-sm font-semibold hover:bg-gray-50">
              Voltar
            </button>
            <button onClick={() => confirmar.mutate()}
              disabled={confirmar.isPending}
              className="flex-1 bg-[#0f2744] text-white rounded-xl py-3 text-sm font-semibold hover:bg-[#1a9e8f] disabled:opacity-50 transition-colors">
              {confirmar.isPending ? "Importando..." : `Importar LTCAT e ${analise.total_agentes} agentes →`}
            </button>
          </div>
        </div>
      )}

      {/* ETAPA 3 — RESULTADO */}
      {etapa === "resultado" && resultado && (
        <div className="space-y-4">
          <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center">
            <CheckCircle size={40} className="mx-auto text-green-500 mb-3" />
            <p className="font-bold text-lg text-gray-900">{resultado.mensagem}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
              <p className="text-2xl font-bold text-green-600">{resultado.agentes_criados}</p>
              <p className="text-xs text-gray-500 mt-1">Agentes nocivos criados</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 text-center">
              <p className="text-sm font-bold text-[#0f2744] mt-2">{resultado.documento_titulo}</p>
              <p className="text-xs text-gray-500 mt-1">Documento registrado</p>
            </div>
          </div>

          {resultado.requer_revisao && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-700 flex items-start gap-2">
              <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
              <span>Acesse <strong>Agentes Nocivos</strong> para revisar os dados extraídos antes de enviar ao eSocial.</span>
            </div>
          )}

          <button onClick={() => { setEtapa("upload"); setAnalise(null); setResultado(null); setArquivo(null); }}
            className="w-full border border-gray-200 text-gray-600 rounded-xl py-3 text-sm font-semibold hover:bg-gray-50">
            Importar outro documento
          </button>
        </div>
      )}
    </div>
  );
}
