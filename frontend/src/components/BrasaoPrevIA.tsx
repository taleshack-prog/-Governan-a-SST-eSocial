// frontend/src/components/BrasaoPrevIA.tsx — AJUSTAPREV
// Brasão da PrevIA: o escudo técnico da marca, usado como avatar da assistente.
//
// DESENHADO PARA 24px, NÃO PARA 64px. O brasão aparece em cinco lugares, e o menor deles é o
// avatar ao lado de cada mensagem do chat, com 24px. Nesse tamanho a grade fina do original
// some — vira um cinza sujo. Então a leitura é sustentada pela silhueta do escudo e pela barra
// de luz; a grade entra por baixo, com opacidade que a faz aparecer só quando há pixel para ela
// (no botão flutuante, de 64px).
//
// É componente, e não <img src>: assim o ícone herda o tamanho de quem o usa, fica nítido em
// qualquer escala e não custa uma requisição por mensagem na tela.
import { useId } from "react";

export function BrasaoPrevIA({ className = "" }: { className?: string }) {
  // Vários avatares convivem na mesma tela (um por mensagem). IDs de gradiente e de clip são
  // globais no documento: repetidos, todas as instâncias passariam a usar a primeira definição.
  const id = useId().replace(/:/g, "");

  return (
    <svg viewBox="0 0 64 64" className={className} role="img" aria-label="PrevIA">
      <title>PrevIA</title>
      <defs>
        <radialGradient id={`f${id}`} cx="0.3" cy="0.22" r="0.95">
          <stop offset="0" stopColor="#15304f" />
          <stop offset="1" stopColor="#07101d" />
        </radialGradient>
        {/* A barra é a parte mais clara do brasão: no original ela é a fenda de luz que corta o
            escudo. É o que identifica o ícone quando tudo o mais vira mancha. */}
        <linearGradient id={`b${id}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#1C5FA8" stopOpacity="0.25" />
          <stop offset="0.5" stopColor="#8FD0FF" />
          <stop offset="1" stopColor="#1C5FA8" stopOpacity="0.25" />
        </linearGradient>
        <linearGradient id={`c${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7FB6F0" />
          <stop offset="1" stopColor="#2B63A8" />
        </linearGradient>
        <pattern id={`g${id}`} width="4" height="4" patternUnits="userSpaceOnUse">
          <path d="M0 0H4M0 0V4" stroke="#9FC4EA" strokeOpacity="0.55" strokeWidth="0.4" fill="none" />
        </pattern>
        <clipPath id={`s${id}`}>
          <path d="M18 16H46V34.5C46 41 40 46.5 32 51C24 46.5 18 41 18 34.5Z" />
        </clipPath>
      </defs>

      <circle cx="32" cy="32" r="32" fill={`url(#f${id})`} />
      <g clipPath={`url(#s${id})`}>
        <rect x="18" y="16" width="28" height="35" fill="#0E2744" />
        <rect x="18" y="16" width="28" height="35" fill={`url(#g${id})`} />
      </g>
      <path d="M18 16H46V34.5C46 41 40 46.5 32 51C24 46.5 18 41 18 34.5Z" fill="none"
            stroke={`url(#c${id})`} strokeWidth="2.2" strokeLinejoin="round" />
      <rect x="15.5" y="30.2" width="33" height="3.6" rx="0.6" fill={`url(#b${id})`} />
    </svg>
  );
}
