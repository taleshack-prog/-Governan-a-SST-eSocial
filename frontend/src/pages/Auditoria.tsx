// ==============================================================
// SST ESOCIAL GOV — Página: Auditoria
// Arquivo: frontend/src/pages/Auditoria.tsx
// ==============================================================

import { useState } from "react";
import { ScrollText, Filter } from "lucide-react";
import { useAuditoria } from "../hooks/useQueries";
import { Card, SectionTitle, Spinner, EmptyState } from "../components/ui";

const TABELAS = ["", "documentos_tecnicos", "agentes_nocivos", "exames_medicos", "cat_registros", "ai_validacoes"];

const OP_CLASSES: Record<string, string> = {
  INSERT: "bg-green-100 text-green-700",
  UPDATE: "bg-blue-100 text-blue-700",
  DELETE: "bg-red-100 text-red-700",
};

export function Auditoria() {
  const [filtroTabela, setFiltroTabela] = useState("");
  const { data: logs = [], isLoading } = useAuditoria(filtroTabela || undefined);

  return (
    <div>
      <SectionTitle
        title="Trilha de Auditoria"
        subtitle="Registro imutável com hash SHA-256 encadeado. Toda alteração é registrada e não pode ser apagada."
      />

      <div className="flex items-center gap-3 mb-6">
        <Filter size={16} className="text-gray-400" />
        <select
          value={filtroTabela}
          onChange={(e) => setFiltroTabela(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {TABELAS.map((t) => (
            <option key={t} value={t}>{t || "Todas as tabelas"}</option>
          ))}
        </select>
        <span className="ml-auto text-xs text-gray-400">
          {logs.length} registro(s)
        </span>
      </div>

      <Card>
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : logs.length === 0 ? (
          <EmptyState message="Nenhum registro de auditoria." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">ID</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Tabela</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Operação</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Registro</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Hash</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Data/Hora</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log: any) => (
                  <tr key={log.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-3 text-gray-400 font-mono text-xs">{log.id}</td>
                    <td className="py-3 px-3 text-gray-700 font-mono text-xs">{log.tabela}</td>
                    <td className="py-3 px-3">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${OP_CLASSES[log.operacao] ?? "bg-gray-100 text-gray-600"}`}>
                        {log.operacao}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-xs text-gray-500">{log.registro_id?.slice(0, 8)}…</td>
                    <td className="py-3 px-3 font-mono text-xs text-gray-400" title={log.hash_atual}>
                      {log.hash_atual?.slice(0, 16)}…
                    </td>
                    <td className="py-3 px-3 text-gray-500 text-xs">
                      {new Date(log.created_at).toLocaleString("pt-BR")}
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
