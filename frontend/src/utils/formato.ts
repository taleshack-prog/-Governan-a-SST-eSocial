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

/** Percentual: "2,00%".
 *  DUAS casas por natureza do número (revisão de 19/10, item 7): alíquota é percentual e se
 *  expressa com duas. Quatro casas são do FAP, que é multiplicador — ali a quarta casa altera
 *  o resultado. Misturar as duas no mesmo bloco chama atenção para a formatação quando deveria
 *  chamar atenção para o número. O valor segue armazenado com quatro casas; aqui é exibição. */
export const pct = (v: number | null | undefined, casas = 2): string =>
  v == null || Number.isNaN(v) ? "—" : `${num(v, casas)}%`;

/** CNAE no formato oficial: 4712100 → "4712-1/00" (item 6).
 *  É a grafia pela qual contadores e fiscais reconhecem o código; sete dígitos corridos obrigam
 *  quem lê a reconstruir a formatação mentalmente e, num laudo, sugerem transcrição sem cuidado.
 *  Aceita o valor já formatado e o devolve como está. */
export const cnae = (v: string | null | undefined): string => {
  if (!v) return "—";
  const d = String(v).replace(/\D/g, "");
  if (d.length !== 7) return String(v);          // já formatado, ou fora do padrão: não inventa
  return `${d.slice(0, 4)}-${d.slice(4, 5)}/${d.slice(5)}`;
};

/** Pontos percentuais com sinal explícito: "+2,00 p.p." / "−1,00 p.p."
 *  Usa o sinal de menos tipográfico (−), não o hífen, para não ser lido como traço. */
export const pp = (v: number | null | undefined, casas = 2): string => {
  if (v == null || Number.isNaN(v)) return "—";
  const sinal = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sinal}${num(Math.abs(v), casas)} p.p.`;
};

/** Máscara progressiva de CNAE, para campo em digitação: aplica o que já cabe. */
export const cnaeParcial = (v: string | null | undefined): string => {
  const d = String(v || "").replace(/\D/g, "").slice(0, 7);
  if (d.length <= 4) return d;
  if (d.length === 5) return `${d.slice(0, 4)}-${d.slice(4)}`;
  return `${d.slice(0, 4)}-${d.slice(4, 5)}/${d.slice(5)}`;
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

// CNPJ com pontuação: 90244278000105 -> 90.244.278/0001-05 (Carolina, 27/10).
// Só formata o que tem 14 dígitos. CNO e CAEPF têm outros formatos e passam inteiros: inventar
// pontuação em documento que não é CNPJ seria pior do que não formatar.
export const cnpj = (v?: string | null): string => {
  const d = (v || "").replace(/\D/g, "");
  if (d.length !== 14) return v || "—";
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
};

// "matriz" -> "Matriz". A natureza do estabelecimento é a posição dele na empresa; o tipo de
// documento vai entre parênteses, como na folha: "Matriz (CNPJ)".
export const natureza = (posicao?: string | null, tipo?: string | null): string => {
  const p = (posicao || "").trim();
  const rotulo = p ? p.charAt(0).toUpperCase() + p.slice(1) : "";
  if (rotulo && tipo) return `${rotulo} (${tipo})`;
  return rotulo || tipo || "—";
};
