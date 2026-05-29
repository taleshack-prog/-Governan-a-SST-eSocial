// ==============================================================
// SST ESOCIAL GOV — Página: Documentos
// Arquivo: frontend/src/pages/Documentos.tsx
// ==============================================================

import { useState, useRef } from "react";
import { Upload, Brain, Filter, FileText, Eye } from "lucide-react";
import { useDocumentos, useUploadDocumento, useSolicitarValidacao } from "../hooks/useQueries";
import { StatusBadge, Card, SectionTitle, Spinner, EmptyState } from "../components/ui";

const TIPOS_DOC = ["", "LTCAT", "PGR", "PCMSO", "ASO", "CAT", "AET", "OUTRO"];

export function Documentos() {
  const [filtroTipo, setFiltroTipo] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: documentos = [], isLoading } = useDocumentos(filtroTipo || undefined);
  const uploadMutation = useUploadDocumento();
  const validarMutation = useSolicitarValidacao();

  // Form state
  const [form, setForm] = useState({ tipo: "LTCAT", titulo: "", data_emissao: "", responsavel_nome: "" });

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    const fd = new FormData();
    fd.append("tipo", form.tipo);
    fd.append("titulo", form.titulo);
    fd.append("data_emissao", form.data_emissao);
    if (form.responsavel_nome) fd.append("responsavel_nome", form.responsavel_nome);
    fd.append("file", file);

    await uploadMutation.mutateAsync(fd);
    setShowUpload(false);
    setForm({ tipo: "LTCAT", titulo: "", data_emissao: "", responsavel_nome: "" });
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div>
      <SectionTitle
        title="Documentos Técnicos"
        subtitle="LTCAT, PGR, PCMSO, ASO, CAT, AET — gestão centralizada com validação IA"
      />

      {/* Actions */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gray-400" />
          <select
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {TIPOS_DOC.map((t) => (
              <option key={t} value={t}>{t || "Todos os tipos"}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="ml-auto flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Upload size={16} />
          Enviar Documento
        </button>
      </div>

      {/* Upload Form */}
      {showUpload && (
        <Card className="mb-6 border-indigo-200 bg-indigo-50">
          <h3 className="font-semibold text-gray-800 mb-4">Novo Documento</h3>
          <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tipo *</label>
              <select
                value={form.tipo}
                onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                required
              >
                {TIPOS_DOC.filter(Boolean).map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Título *</label>
              <input
                value={form.titulo}
                onChange={(e) => setForm({ ...form, titulo: e.target.value })}
                placeholder="Ex: LTCAT — Setor de Caldeiraria 2025"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Data de Emissão *</label>
              <input
                type="date"
                value={form.data_emissao}
                onChange={(e) => setForm({ ...form, data_emissao: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Responsável Técnico</label>
              <input
                value={form.responsavel_nome}
                onChange={(e) => setForm({ ...form, responsavel_nome: e.target.value })}
                placeholder="Nome do Eng. de Segurança ou Médico"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Arquivo (PDF ou DOCX) *</label>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.doc"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                required
              />
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button
                type="submit"
                disabled={uploadMutation.isPending}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              >
                {uploadMutation.isPending ? <Spinner size={16} /> : <Upload size={16} />}
                {uploadMutation.isPending ? "Enviando..." : "Enviar"}
              </button>
              <button
                type="button"
                onClick={() => setShowUpload(false)}
                className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-lg border border-gray-300"
              >
                Cancelar
              </button>
            </div>
          </form>
        </Card>
      )}

      {/* Tabela */}
      <Card>
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner size={28} /></div>
        ) : documentos.length === 0 ? (
          <EmptyState message="Nenhum documento encontrado. Envie o primeiro documento." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Tipo</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Título</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Emissão</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Validade</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Status</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Versão</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {documentos.map((doc: any) => (
                  <tr key={doc.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-3">
                      <span className="bg-indigo-100 text-indigo-700 text-xs font-semibold px-2 py-0.5 rounded">
                        {doc.tipo}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-medium text-gray-800 max-w-xs truncate" title={doc.titulo}>
                      {doc.titulo}
                    </td>
                    <td className="py-3 px-3 text-gray-500">{doc.data_emissao}</td>
                    <td className="py-3 px-3 text-gray-500">{doc.data_validade ?? "—"}</td>
                    <td className="py-3 px-3"><StatusBadge status={doc.status} /></td>
                    <td className="py-3 px-3 text-gray-500">v{doc.versao}</td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => validarMutation.mutate(doc.id)}
                          disabled={validarMutation.isPending}
                          title="Validar com IA"
                          className="flex items-center gap-1 text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 px-2 py-1 rounded transition-colors"
                        >
                          <Brain size={13} />
                          IA
                        </button>
                        <button
                          title="Ver detalhes"
                          className="flex items-center gap-1 text-xs bg-gray-50 hover:bg-gray-100 text-gray-600 px-2 py-1 rounded transition-colors"
                        >
                          <Eye size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
