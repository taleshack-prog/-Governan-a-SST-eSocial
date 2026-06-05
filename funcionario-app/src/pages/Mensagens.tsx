import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, MessageCircle } from "lucide-react";
import { api } from "../api/client";

export default function Mensagens() {
  const qc = useQueryClient();
  const [texto, setTexto] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const token = localStorage.getItem("radar_func_token");

  const { data: afastamentos = [] } = useQuery({
    queryKey: ["meus-afastamentos"],
    queryFn: async () => {
      const r = await api.get("/funcionarios/auth/meus-afastamentos", {
        headers: { Authorization: `Bearer ${token}` }
      });
      return r.data;
    },
  });

  const afastamento = afastamentos[0];

  const { data: mensagens = [], isLoading } = useQuery({
    queryKey: ["mensagens", afastamento?.id],
    enabled: !!afastamento?.id,
    refetchInterval: 5000,
    queryFn: async () => {
      const r = await api.get(`/afastamentos/${afastamento.id}/mensagens`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return r.data;
    },
  });

  const enviar = useMutation({
    mutationFn: async (msg: string) => {
      await api.post(`/afastamentos/${afastamento.id}/mensagens`,
        { mensagem: msg, remetente_tipo: "funcionario" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    },
    onSuccess: () => {
      setTexto("");
      qc.invalidateQueries({ queryKey: ["mensagens", afastamento?.id] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens]);

  const formatHora = (dt: string) => {
    return new Date(dt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  };

  const formatData = (dt: string) => {
    return new Date(dt).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  };

  if (!afastamento) {
    return (
      <div className="min-h-screen bg-[#f5f6fa] pb-24">
        <div className="bg-[#0f2744] text-white px-5 pt-12 pb-6">
          <h1 className="text-2xl font-bold">Mensagens</h1>
          <p className="text-blue-300 text-sm mt-0.5">Comunicação com o RH</p>
        </div>
        <div className="px-4 mt-4">
          <div className="bg-white rounded-2xl p-8 shadow-sm flex flex-col items-center gap-3">
            <MessageCircle size={48} color="#1a9e8f" />
            <p className="text-gray-600 text-sm text-center">
              Nenhum afastamento ativo.<br />Não há mensagens para exibir.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#f5f6fa]">
      {/* Header */}
      <div className="bg-[#0f2744] text-white px-5 pt-12 pb-4 flex-shrink-0">
        <h1 className="text-xl font-bold">Mensagens</h1>
        <p className="text-blue-300 text-sm mt-0.5">Comunicação com o RH</p>
      </div>

      {/* Chat */}
      <div className="flex-1 overflow-y-auto px-4 py-4 pb-2">
        {isLoading && (
          <div className="text-center text-gray-400 text-sm py-8">Carregando mensagens...</div>
        )}

        {mensagens.length === 0 && !isLoading && (
          <div className="flex flex-col items-center gap-2 py-12">
            <MessageCircle size={40} color="#d1d5db" />
            <p className="text-gray-400 text-sm text-center">Nenhuma mensagem ainda.<br />Envie uma mensagem para o RH.</p>
          </div>
        )}

        {mensagens.map((m: any, i: number) => {
          const isMeu = m.remetente_tipo === "funcionario";
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
              <div className={`flex mb-2 ${isMeu ? "justify-end" : "justify-start"}`}>
                {!isMeu && (
                  <div className="w-7 h-7 rounded-full bg-[#0f2744] flex items-center justify-center text-white text-xs font-bold mr-2 flex-shrink-0 self-end mb-1">
                    RH
                  </div>
                )}
                <div className={`max-w-[75%] ${isMeu ? "items-end" : "items-start"} flex flex-col`}>
                  <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                    isMeu
                      ? "bg-[#1a9e8f] text-white rounded-br-sm"
                      : "bg-white text-gray-800 shadow-sm rounded-bl-sm"
                  }`}>
                    {m.mensagem}
                  </div>
                  <span className="text-xs text-gray-400 mt-1 px-1">{formatHora(m.created_at)}</span>
                </div>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-100 px-4 py-3 pb-8 flex-shrink-0">
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
            className="flex-1 bg-gray-100 rounded-2xl px-4 py-3 text-sm resize-none outline-none max-h-24"
            style={{ lineHeight: "1.4" }}
          />
          <button
            onClick={() => { if (texto.trim()) enviar.mutate(texto.trim()); }}
            disabled={!texto.trim() || enviar.isPending}
            className="w-11 h-11 bg-[#1a9e8f] rounded-full flex items-center justify-center flex-shrink-0 disabled:opacity-40"
          >
            <Send size={18} color="white" />
          </button>
        </div>
      </div>
    </div>
  );
}
