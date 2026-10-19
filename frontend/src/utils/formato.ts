// frontend/src/utils/formato.ts — SST ESOCIAL GOV
// Formatação numérica em português (item 2 da revisão da Carolina).
//
// Vírgula como separador decimal, ponto reservado para milhar. Esses números vão para documento
// entregue a cliente e eventualmente a fiscal: ponto decimal, lido por um contador brasileiro,
// parece defeito de sistema — e um sistema que parece defeituoso na formatação perde
// credibilidade no conteúdo.
//
// Usar estas funções em vez de toFixed em qualquer número que apareça na tela.

/** Número com casas fixas, separador decimal vírgula e milhar com ponto. */
export const num = (v: number | null | undefined, casas = 2): string =>
  v == null || Number.isNaN(v)
    ? "—"
    : v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

/** Percentual: "2,00%" */
export const pct = (v: number | null | undefined, casas = 2): string =>
  v == null || Number.isNaN(v) ? "—" : `${num(v, casas)}%`;

/** Pontos percentuais com sinal explícito: "+2,00 p.p." / "−1,00 p.p."
 *  Usa o sinal de menos tipográfico (−), não o hífen, para não ser lido como traço. */
export const pp = (v: number | null | undefined, casas = 2): string => {
  if (v == null || Number.isNaN(v)) return "—";
  const sinal = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sinal}${num(Math.abs(v), casas)} p.p.`;
};

/** Data ISO (YYYY-MM-DD) para DD/MM/AAAA. */
export const data = (iso?: string | null): string =>
  iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "—";

/** Competência ISO para MM/AAAA. */
export const competencia = (iso?: string | null): string =>
  iso ? `${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "—";

/** Data e hora ISO para DD/MM/AAAA às HH:MM, no fuso local. */
export const dataHora = (iso?: string | null): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.toLocaleDateString("pt-BR")} às ${d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
};
