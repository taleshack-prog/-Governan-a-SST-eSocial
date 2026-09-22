// ==============================================================
// SST ESOCIAL GOV — Página: Fila de Classificação (Caixa 3)
// Arquivo: frontend/src/pages/FilaClassificacao.tsx
// ==============================================================

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface ItemFila {
  id: string;
  estabelecimento_id: string;
  estabelecimento_nome: string | null;
  descricao: string;
  codigo_esocial: string | null;
  valor_mensal: number;
  incide_inss_praticado: boolean;
  rubrica_dicionario: string;
  condicao: string | null;
  grau_seguranca: string;
  fundamento?: string;
}

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function FilaClassificacao() {
  const qc = useQueryClient();
  const [justif, setJustif] = useState<Record<string, string>>({});

  const { data: itens = [], isLoading } = useQuery<ItemFila[]>({
    queryKey: ["fila-classificacao"],
    queryFn: () => apiClient.get("/rubricas/fila-classificacao").then((r) => r.data),
  });

  const classificar = useMutation({
    mutationFn: ({ id, classificacao }: { id: string; classificacao: string }) =>
      apiClient.put(`/rubricas/${id}/classificar`, {
        classificacao,
        justificativa: justif[id] || null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fila-classificacao"] }),
  });

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Fila de Classificação</h1>
        <p className="text-gray-600 mt-1">
          Rubricas <strong>condicionais</strong> (Caixa 3): a incidência depende da forma de
          pagamento. Decida caso a caso — só então o comparador libera crédito ou trava a rubrica.
        </p>
      </div>

      {isLoading && <p className="text-gray-500">Carregando…</p>}

      {!isLoading && itens.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center">
          <p className="text-green-800 font-medium">Nenhuma rubrica pendente de classificação.</p>
          <p className="text-green-700 text-sm mt-1">
            Rode o comparador na tela de Diagnóstico para trazer rubricas condicionais, se houver.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {itens.map((it) => (
          <div key={it.id} className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-gray-900">{it.descricao}</h3>
                <p className="text-sm text-gray-500">
                  {it.estabelecimento_nome || "—"}
                  {it.codigo_esocial ? ` · cod. ${it.codigo_esocial}` : ""}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs text-gray-400">valor mensal</p>
                <p className="font-bold text-gray-900">{brl(it.valor_mensal)}</p>
              </div>
            </div>

            {it.condicao && (
              <div className="mt-3 bg-amber-50 border border-amber-200 rounded-xl p-3">
                <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">
                  Guia de decisao
                </p>
                <p className="text-sm text-amber-900 mt-0.5">{it.condicao}</p>
              </div>
            )}

            {it.fundamento && (
              <p className="mt-2 text-xs text-gray-500">
                <span className="font-semibold">Fundamento:</span> {it.fundamento}
              </p>
            )}

            <textarea
              className="mt-3 w-full border border-gray-300 rounded-xl p-2 text-sm"
              rows={2}
              placeholder="Justificativa da decisao (opcional, recomendavel para a defesa)..."
              value={justif[it.id] || ""}
              onChange={(e) => setJustif((p) => ({ ...p, [it.id]: e.target.value }))}
            />

            <div className="mt-3 flex gap-3">
              <button
                onClick={() => classificar.mutate({ id: it.id, classificacao: "nao_incide" })}
                disabled={classificar.isPending}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl py-2 font-medium disabled:opacity-50"
              >
                Nao incide -&gt; gera credito
              </button>
              <button
                onClick={() => classificar.mutate({ id: it.id, classificacao: "incide" })}
                disabled={classificar.isPending}
                className="flex-1 bg-slate-600 hover:bg-slate-700 text-white rounded-xl py-2 font-medium disabled:opacity-50"
              >
                Incide -&gt; mantem (trava)
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
