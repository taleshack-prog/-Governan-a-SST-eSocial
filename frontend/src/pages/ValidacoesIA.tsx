// ==============================================================
// SST ESOCIAL GOV — Página: Validações IA
// Arquivo: frontend/src/pages/ValidacoesIA.tsx
// ==============================================================

import { useState } from "react";
import { Brain, ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, ThumbsUp, ThumbsDown } from "lucide-react";
import { useValidacoes, useValidacao } from "../hooks/useQueries";
import { Card, SectionTitle, Spinner, EmptyState, StatusBadge, GradeBadge } from "../components/ui";
import { validacoesApi } from "../api/client";
import toast from "react-hot-toast";

function ValidacaoDetail({ id }: { id: string }) {
  const { data: val, isLoading } = useValidacao(id);

  async function darFeedback(correto: boolean) {
    try {
      await validacoesApi.feedback(id, { correto, rating: correto ? 5 : 2 });
      toast.success("Feedback registrado! Obrigado.");
    } catch {
      toast.error("Erro ao registrar feedback.");
    }
  }

  if (isLoading) return <div className="py-4 flex justify-center"><Spinner /></div>;
  if (!val) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
      {/* Erros */}
      {val.erros?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-red-700 uppercase tracking-wide">Erros detectados</p>
          {val.erros.map((e: string, i: number) => (
            <div key={i} className="flex items-start gap-2 text-xs text-red-600 bg-red-50 rounded px-2 py-1">
              <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
              {e}
            </div>
          ))}
        </div>
      )}

      {/* Alertas */}
      {val.alertas?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-yellow-700 uppercase tracking-wide">Alertas</p>
          {val.alertas.map((a: string, i: number) => (
            <div key={i} className="flex items-start gap-2 text-xs text-yellow-700 bg-yellow-50 rounded px-2 py-1">
              <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
              {a}
            </div>
          ))}
        </div>
      )}

      {/* Sugestões */}
      {val.sugestoes?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Sugestões IA</p>
          {val.sugestoes.map((s: string, i: number) => (
            <div key={i} className="flex items-start gap-2 text-xs text-blue-700 bg-blue-50 rounded px-2 py-1">
              <Brain size={12} className="mt-0.5 flex-shrink-0" />
              {s}
            </div>
          ))}
        </div>
      )}

      {/* Feedback */}
      <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
        <p className="text-xs text-gray-500">O resultado foi correto?</p>
        <button onClick={() => darFeedback(true)} className="flex items-center gap-1 text-xs text-green-600 hover:text-green-700 bg-green-50 hover:bg-green-100 px-2 py-1 rounded transition-colors">
          <ThumbsUp size={13} /> Sim
        </button>
        <button onClick={() => darFeedback(false)} className="flex items-center gap-1 text-xs text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-2 py-1 rounded transition-colors">
          <ThumbsDown size={13} /> Não
        </button>
      </div>
    </div>
  );
}

export function ValidacoesIA() {
  const { data: validacoes = [], isLoading } = useValidacoes();
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div>
      <SectionTitle
        title="Validações com Inteligência Artificial"
        subtitle="Pipeline de 9 etapas — RAG normativo + anti-alucinação + score GRADE"
      />

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size={32} /></div>
      ) : validacoes.length === 0 ? (
        <Card><EmptyState message="Nenhuma validação realizada. Envie um documento e clique em 'Validar com IA'." /></Card>
      ) : (
        <div className="space-y-3">
          {validacoes.map((v: any) => (
            <Card key={v.id} className="cursor-pointer hover:shadow-md transition-shadow">
              <div className="flex items-center gap-4" onClick={() => setExpanded(expanded === v.id ? null : v.id)}>
                <div className="p-2 bg-purple-50 rounded-lg">
                  <Brain size={20} className="text-purple-600" />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-800 text-sm">{v.tipo_validacao}</p>
                  <p className="text-xs text-gray-400">{new Date(v.created_at).toLocaleString("pt-BR")}</p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={v.status} />
                  {v.grade_label && <GradeBadge grade={v.grade_label} />}
                  {v.confidence_score != null && (
                    <span className="text-sm text-gray-500 font-mono">
                      {(v.confidence_score * 100).toFixed(0)}%
                    </span>
                  )}
                  {v.needs_human_review && (
                    <span className="flex items-center gap-1 text-xs text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded">
                      <AlertTriangle size={12} /> Revisar
                    </span>
                  )}
                  {expanded === v.id ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                </div>
              </div>

              {expanded === v.id && <ValidacaoDetail id={v.id} />}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
