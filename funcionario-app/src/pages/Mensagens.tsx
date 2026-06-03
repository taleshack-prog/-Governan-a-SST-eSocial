import { MessageCircle } from "lucide-react";

export default function Mensagens() {
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
            Nenhuma mensagem ainda.<br/>Use <strong>Falar com RH</strong> na tela de afastamento.
          </p>
        </div>
      </div>
    </div>
  );
}
