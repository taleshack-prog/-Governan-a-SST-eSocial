// ==============================================================
// RADAR PREVIDENCIÁRIO — Chat RH ↔ Funcionário
// Arquivo: frontend/src/components/ChatAfastamento.tsx
// ==============================================================
import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, MessageCircle, X } from "lucide-react";
import { apiClient } from "../api/client";

interface Props {
  afastamentoId: string;
  nomeTrabalhador: string;
  onClose: () => void;
}

export default function ChatAfastamento({ afastamentoId, nomeTrabalhador, onClose }: Props) {
  const qc = useQueryClient();
  const [texto, setTexto] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: mensagens = [], isLoading } = useQuery({
    queryKey: ["chat", afastamentoId],
    refetchInterval: 5000,
    queryFn: () => apiClient.get(`/afastamentos/${afastamentoId}/mensagens`).then(r => r.data),
  });

  const enviar = useMutation({
    mutationFn: (msg: string) => apiClient.post(`/afastamentos/${afastamentoId}/mensagens`, {
      mensagem: msg,
      remetente_tipo: "rh",
    }),
    onSuccess: () => {
      setTexto("");
      qc.invalidateQueries({ queryKey: ["chat", afastamentoId] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens]);

  const formatHora = (dt: string) =>
    new Date(dt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  const formatData = (dt: string) =>
    new Date(dt).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40">
      <div className="bg-white w-full sm:w-[420px] sm:rounded-2xl flex flex-col" style={{ height: "85vh", maxHeight: "600px" }}>
        
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#0f2744] flex items-center justify-center">
              <MessageCircle size={16} color="white" />
            </div>
            <div>
              <p className="font-semibold text-sm text-gray-900">{nomeTrabalhador}</p>
              <p className="text-xs text-gray-400">Chat com funcionário</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
            <X size={16} />
          </button>
        </div>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {isLoading && (
            <div className="text-center text-gray-400 text-sm py-8">Carregando...</div>
          )}

          {mensagens.length === 0 && !isLoading && (
            <div className="flex flex-col items-center gap-2 py-10">
              <MessageCircle size={36} color="#d1d5db" />
              <p className="text-gray-400 text-sm text-center">Nenhuma mensagem ainda.</p>
            </div>
          )}

          {mensagens.map((m: any, i: number) => {
            const isRH = m.remetente_tipo === "rh";
            const dataAnterior = i > 0 ? formatData(mensagens[i - 1].created_at) : null;
            const dataAtual = formatData(m.created_at);
            const mostrarData = dataAtual !== dataAnterior;

            return (
              <div key={m.id}>
                {mostrarData && (
                  <div className="text-center my-3">
                    <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">{dataAtual}</span>
                  </div>
                )}
                <div className={`flex mb-2 ${isRH ? "justify-end" : "justify-start"}`}>
                  {!isRH && (
                    <div className="w-6 h-6 rounded-full bg-[#1a9e8f] flex items-center justify-center text-white text-xs font-bold mr-2 flex-shrink-0 self-end mb-1">
                      F
                    </div>
                  )}
                  <div className={`max-w-[75%] flex flex-col ${isRH ? "items-end" : "items-start"}`}>
                    <div className={`px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                      isRH
                        ? "bg-[#0f2744] text-white rounded-br-sm"
                        : "bg-gray-100 text-gray-800 rounded-bl-sm"
                    }`}>
                      {m.mensagem}
                    </div>
                    <span className="text-xs text-gray-400 mt-1">{formatHora(m.created_at)}</span>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-100 px-4 py-3 flex-shrink-0">
          <div className="flex gap-2 items-end">
            <textarea
              value={texto}
              onChange={e => setTexto(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (texto.trim()) enviar.mutate(texto.trim());
                }
              }}
              placeholder="Escreva uma mensagem..."
              rows={1}
              className="flex-1 bg-gray-100 rounded-2xl px-4 py-2.5 text-sm resize-none outline-none max-h-24"
            />
            <button
              onClick={() => { if (texto.trim()) enviar.mutate(texto.trim()); }}
              disabled={!texto.trim() || enviar.isPending}
              className="w-10 h-10 bg-[#0f2744] rounded-full flex items-center justify-center flex-shrink-0 disabled:opacity-40"
            >
              <Send size={16} color="white" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
