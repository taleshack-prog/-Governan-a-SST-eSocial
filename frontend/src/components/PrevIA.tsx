import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { X, Send, Minimize2 } from "lucide-react";
import { apiClient } from "../api/client";
import { useLocation } from "react-router-dom";

interface Mensagem {
  role: "user" | "assistant";
  content: string;
}

const SUGESTOES: Record<string, string[]> = {
  dashboard:          ["Me explica essa tela", "O que devo fazer agora?", "Quais alertas são críticos?"],
  afastamentos:       ["Como criar um afastamento?", "O que é limbo judicial?", "Como confirmar retorno?"],
  "radar-financeiro": ["Me explica essa tela", "Como reduzir as perdas?", "O que é o score de pressão?"],
  inconsistencias:    ["O que são inconsistências?", "Como corrigir pendências?", "O que é checklist pré-eSocial?"],
  tendencias:         ["Como interpretar o ranking?", "O que é capacidade reduzida?", "Como funciona a previsão?"],
  trabalhadores:      ["Como cadastrar trabalhador?", "O que é vínculo empregatício?"],
  documentos:         ["O que é LTCAT?", "O que é PCMSO?", "Por que o documento venceu?"],
  ppp:                ["O que é PPP?", "Quando o PPP é obrigatório?", "Como gerar o PDF?"],
  radar:              ["O que é o score de risco?", "Como reduzir o risco?"],
};

function fmt(texto: string) {
  return texto
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/^## (.*)/gm, "<p class='font-bold text-gray-900 mt-2 mb-1'>$1</p>")
    .replace(/^# (.*)/gm, "<p class='font-bold text-gray-900 mt-2 mb-1'>$1</p>")
    .replace(/^- (.*)/gm, "<div class='flex gap-1.5'><span class='text-teal-500'>•</span><span>$1</span></div>")
    .replace(/\n/g, "<br>");
}

export default function PrevIA() {
  const [aberto, setAberto] = useState(false);
  const [minimizado, setMinimizado] = useState(false);
  const [texto, setTexto] = useState("");
  const [historico, setHistorico] = useState<Mensagem[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const tela = location.pathname.replace("/", "") || "dashboard";
  const sugestoes = SUGESTOES[tela] || SUGESTOES.dashboard;

  const enviar = useMutation({
    mutationFn: (msg: string) =>
      apiClient.post("/previa/chat", { mensagem: msg, tela_atual: tela, historico: historico.slice(-6) }).then(r => r.data),
    onSuccess: (data) => setHistorico(prev => [...prev, { role: "assistant", content: data.resposta }]),
    onError: () => setHistorico(prev => [...prev, { role: "assistant", content: "Ocorreu um erro. Tente novamente." }]),
  });

  const handleEnviar = (msg?: string) => {
    const m = msg || texto.trim();
    if (!m) return;
    setHistorico(prev => [...prev, { role: "user", content: m }]);
    setTexto("");
    enviar.mutate(m);
  };

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [historico]);
  useEffect(() => { setHistorico([]); }, [tela]);

  if (!aberto) return (
    <button onClick={() => setAberto(true)}
      className="fixed bottom-6 right-6 z-50 w-16 h-16 rounded-full shadow-lg overflow-hidden border-3 border-[#1a9e8f] hover:scale-110 transition-all"
      title="PrevIA">
      <img src="/previa-avatar.jpeg" alt="PrevIA" className="w-full h-full object-cover" />
      <span className="absolute top-0 right-0 w-4 h-4 bg-green-400 rounded-full border-2 border-white animate-pulse" />
    </button>
  );

  return (
    <div className={`fixed bottom-6 right-6 z-50 flex flex-col bg-white rounded-2xl shadow-2xl border border-gray-100 transition-all ${minimizado ? "w-72 h-14" : "w-80 sm:w-96 h-[520px]"}`}>
      <div className="flex items-center justify-between px-4 py-3 bg-[#0f2744] rounded-t-2xl flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <img src="/previa-avatar.jpeg" alt="PrevIA" className="w-8 h-8 rounded-full object-cover border border-[#1a9e8f]" />
          <div>
            <p className="text-white text-sm font-bold">PrevIA</p>
            <p className="text-blue-300 text-xs">Assistente Previdenciária</p>
          </div>
        </div>
        <div className="flex gap-1">
          <button onClick={() => setMinimizado(!minimizado)} className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20">
            <Minimize2 size={13} color="white" />
          </button>
          <button onClick={() => setAberto(false)} className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20">
            <X size={13} color="white" />
          </button>
        </div>
      </div>

      {!minimizado && (
        <>
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {historico.length === 0 && (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <img src="/previa-avatar.jpeg" alt="PrevIA" className="w-6 h-6 rounded-full object-cover flex-shrink-0 mt-0.5" />
                  <div className="bg-gray-50 rounded-2xl rounded-tl-sm px-3 py-2.5 text-xs text-gray-700 max-w-[85%]">
                    Olá! Sou a <strong>PrevIA</strong>. Posso explicar esta tela, orientar tarefas e identificar pendências. Como posso ajudar?
                  </div>
                </div>
                <div className="space-y-1.5 pl-8">
                  {sugestoes.map((s, i) => (
                    <button key={i} onClick={() => handleEnviar(s)}
                      className="block w-full text-left text-xs text-[#1a9e8f] bg-teal-50 border border-teal-200 rounded-xl px-3 py-2 hover:bg-teal-100">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {historico.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                {m.role === "assistant" && (
                  <img src="/previa-avatar.jpeg" alt="PrevIA" className="w-6 h-6 rounded-full object-cover flex-shrink-0 mt-0.5" />
                )}
                <div className={`max-w-[85%] rounded-2xl px-3 py-2.5 text-xs leading-relaxed ${m.role === "user" ? "bg-[#0f2744] text-white rounded-tr-sm" : "bg-gray-50 text-gray-700 rounded-tl-sm"}`}
                  dangerouslySetInnerHTML={{ __html: m.role === "assistant" ? fmt(m.content) : m.content }} />
              </div>
            ))}
            {enviar.isPending && (
              <div className="flex gap-2">
                <img src="/previa-avatar.jpeg" alt="PrevIA" className="w-6 h-6 rounded-full object-cover flex-shrink-0" />
                <div className="bg-gray-50 rounded-2xl rounded-tl-sm px-3 py-2.5">
                  <div className="flex gap-1">
                    {[0,150,300].map(d => <span key={d} className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:`${d}ms`}}/>)}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <div className="border-t border-gray-100 px-3 py-2.5 flex-shrink-0">
            <div className="flex gap-2 items-end">
              <textarea value={texto} onChange={e => setTexto(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleEnviar(); }}}
                placeholder="Pergunte à PrevIA..." rows={1}
                className="flex-1 bg-gray-100 rounded-xl px-3 py-2 text-xs resize-none outline-none max-h-20" />
              <button onClick={() => handleEnviar()} disabled={!texto.trim() || enviar.isPending}
                className="w-8 h-8 bg-[#1a9e8f] rounded-full flex items-center justify-center flex-shrink-0 disabled:opacity-40">
                <Send size={14} color="white" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
