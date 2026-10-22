// frontend/src/components/Fundamentacao.tsx — SST ESOCIAL GOV
// Ícone de fundamentação normativa (item 3 da revisão da Carolina).
//
// A citação NÃO é escrita aqui. Este componente pergunta ao backend qual dispositivo está em
// vigor para o campo, na data de referência, e exibe o que a tabela versionada responder.
// Quando a lei mudar, acrescenta-se linha na tabela e esta tela passa a mostrar o texto novo
// sem alteração de código — que é o ponto: a CPRB mudou três vezes em cinco anos, e fundamento
// revogado com aparência de vigente é pior do que fundamento nenhum.
//
// Se o campo não tiver linha cadastrada, o backend devolve 404 e o ícone simplesmente não
// aparece. Melhor nenhum ícone do que fundamento inventado.
import { useEffect, useRef, useState } from "react";
import { apiClient } from "../api/client";

type Fund = {
  dispositivo: string;
  ato_normativo?: string | null;
  anexo?: string | null;
  observacao?: string | null;
  vigencia_inicio: string;
  vigencia_fim?: string | null;
};

const ymd = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

// Data de hoje em ISO, para os pontos de CADASTRO — campos que o usuário preenche agora e que
// não pertencem a uma competência. Onde existe competência, passa-se a competência: era o
// "default: hoje" escondido no backend que fazia uma peça sobre 2021 citar a redação de 2026.
export const hojeISO = () => new Date().toISOString().slice(0, 10);

// `em` é OBRIGATÓRIO de propósito. O build roda `tsc` antes do `vite`, então esquecer a data em
// qualquer chamada quebra a compilação em vez de voltar silenciosamente a citar a norma de hoje.
export function Fundamentacao({ campo, em }: { campo: string; em: string }) {
  const [f, setF] = useState<Fund | null>(null);
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiClient
      .get(`/fundamentacao/${campo}`, { params: { em } })
      .then((r) => setF(r.data))
      .catch(() => setF(null));   // 404 = sem citação para aquela data: não exibe nada
  }, [campo, em]);

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => {
      if (caixa.current && !caixa.current.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, [aberto]);

  if (!f) return null;

  return (
    <span className="relative inline-block align-middle" ref={caixa}>
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-label={`Fundamentação legal de ${campo}`}
        className="ml-1 w-4 h-4 rounded-full border border-gray-300 text-[10px] leading-none text-gray-500 hover:bg-gray-100 hover:text-gray-700"
      >
        §
      </button>
      {aberto && (
        <div className="absolute z-30 left-0 top-6 w-80 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-left">
          <p className="text-[11px] font-semibold text-gray-700">{f.dispositivo}</p>
          {f.ato_normativo && <p className="text-[11px] text-gray-600 mt-1">{f.ato_normativo}</p>}
          {f.anexo && <p className="text-[11px] text-gray-600">{f.anexo}</p>}
          {f.observacao && <p className="text-[11px] text-gray-500 mt-2">{f.observacao}</p>}
          <p className="text-[10px] text-gray-400 mt-2 pt-2 border-t border-gray-100">
            Vigência: desde {ymd(f.vigencia_inicio)}
            {f.vigencia_fim ? ` até ${ymd(f.vigencia_fim)}` : " — em vigor"}.
          </p>
        </div>
      )}
    </span>
  );
}
