// ==============================================================
// SST ESOCIAL GOV — Estabelecimentos (Adendo 04, v1 / Fase 2)
// O grau de risco é DERIVADO da atividade preponderante (RN-20). Aqui a empresa declara os
// insumos: natureza/datas e a lista de atividades com quantitativo por período.
// ==============================================================
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import * as fmt from "../utils/formato";
import { Fundamentacao, hojeISO } from "../components/Fundamentacao";
import { useParams, useNavigate } from "react-router-dom";

const NATUREZAS = ["CNPJ", "CNO", "CAEPF"];
const POSICOES = ["matriz", "filial", "obra"];
// Os filtros da lista-indice (etapa C, item 3). "Com pendência" e "Encerrados" não são
// naturezas: são recortes de trabalho, e por isso vêm depois dos três de natureza.
const FILTROS: [string, string][] = [
  ["todos", "Todos"], ["matriz", "Matriz"], ["filial", "Filiais"], ["obra", "Obras"],
  ["pendencia", "Com pendência"], ["encerrados", "Encerrados"],
];
const STATUS = ["ativa", "paralisada", "encerrada"];

const maskCnpj = (v: string) => (v || "").replace(/\D/g, "").slice(0, 14)
  .replace(/^(\d{2})(\d)/, "$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
  .replace(/\.(\d{3})(\d)/, ".$1/$2").replace(/(\d{4})(\d)/, "$1-$2");
const validaCnpj = (v: string): boolean => {
  const c = (v || "").replace(/\D/g, "");
  if (c.length !== 14 || /^(\d)\1{13}$/.test(c)) return false;
  const dv = (base: string) => { let s = 0, p = base.length - 7; for (let i = 0; i < base.length; i++) { s += +base[i] * p--; if (p < 2) p = 9; } const r = s % 11; return r < 2 ? 0 : 11 - r; };
  return dv(c.slice(0, 12)) === +c[12] && dv(c.slice(0, 13)) === +c[13];
};

const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];
const maskCep = (v: string) => (v || "").replace(/\D/g, "").slice(0, 8).replace(/^(\d{5})(\d)/, "$1-$2");

// Preenchimento por CEP, mesma fonte da tela da empresa (item 5). Só completa o que está vazio:
// nunca sobrescreve o que o usuário digitou, e string vazia do serviço não apaga valor existente.
async function buscarCep(cepRaw: string, form: any, setForm: (f: any) => void) {
  const d = (cepRaw || "").replace(/\D/g, "");
  if (d.length !== 8) return;
  try {
    const resp = await fetch(`https://viacep.com.br/ws/${d}/json/`);
    const j = await resp.json();
    if (j?.erro) return;
    const ou = (novo: any, atual: any) => (atual && String(atual).trim() ? atual : (novo || atual));
    setForm({
      ...form, cep: maskCep(d),
      endereco: ou(j.logradouro, form.endereco), bairro: ou(j.bairro, form.bairro),
      cidade: ou(j.localidade, form.cidade), uf: ou(j.uf, form.uf),
    });
  } catch { /* CEP indisponível: o usuário preenche à mão */ }
}

const FORM_VAZIO = {
  id: "", codigo: "", nome: "", tipo_estabelecimento: "CNPJ", posicao: "filial",
  cnpj: "", identificador: "", status: "ativa",
  endereco: "", cep: "", numero: "", complemento: "", bairro: "", cidade: "", uf: "",
  data_abertura: "", data_encerramento: "",
};
const inp = "w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm";
const lbl = "text-xs font-medium text-gray-600";
const derivLabel = "block text-[11px] text-gray-500";
const derivVal = "text-lg font-semibold text-gray-900 tabular-nums leading-tight";

// Situação da competência (espelha api/services/enquadramento_situacao.py).
// "apurado" não é "ok": o devido está calculado, mas ninguém informou o que a empresa aplicou.
// Os QUATRO estados da competência. Cada rótulo diz de quem é a afirmação, porque é isso que
// muda a leitura: 'apurado' é o sistema dizendo; 'conferido' é uma pessoa assinando; 'conferência'
// é pendência (falta dado); 'não auditada' é AUSÊNCIA DE OBJETO — o regime afasta a apuração do
// RAT, então não há alíquota devida a comparar. Não confundir com divergência zero.
const SIT: Record<string, { txt: string; cls: string; ajuda: string }> = {
  conferencia: { txt: "conferência", cls: "text-amber-700", ajuda: "Falta dado para apurar o devido." },
  apurado: { txt: "apurado", cls: "text-sky-700", ajuda: "Devido calculado pelo sistema. Nenhuma pessoa conferiu ainda." },
  conferido: { txt: "conferido", cls: "text-emerald-600", ajuda: "Devido e aplicado comparados e validados por uma pessoa." },
  nao_auditada: { txt: "não auditada", cls: "text-gray-500", ajuda: "O regime tributário afasta a apuração do RAT nesta competência." },
};

const mesBR = (iso?: string | null) => (iso ? `${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "—");

// Data e hora da assinatura. A hora entra porque conferir e reapurar podem acontecer no mesmo
// dia, e a ordem entre os dois é o que explica uma conferência revogada. Devolve string vazia
// em vez de "Invalid Date" quando o valor não vem — new Date(null) não falha, mente.
const dataHoraBR = (iso?: string | null): string => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
};

// Origem da divergência: qual das duas declarações do S-1005 saiu errada. A resposta decide a
// defesa — grau se corrige com reenquadramento, FAP com a portaria e o extrato do FAPWeb.
const ORIGEM: Record<string, string> = {
  grau: "origem: grau de risco", fap: "origem: FAP", ambas: "origem: grau e FAP", nenhuma: "",
};

// ---------- Autocomplete de CNAE sobre o Anexo I ----------
function CnaeAutocomplete({ value, onPick }: { value: string; onPick: (c: any) => void }) {
  const [q, setQ] = useState(value || "");
  const [opts, setOpts] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  useEffect(() => { setQ(value || ""); }, [value]);
  useEffect(() => {
    if (q.trim().length < 2) { setOpts([]); return; }
    const t = setTimeout(() => {
      apiClient.get(`/cnae/buscar`, { params: { q } }).then((r) => setOpts(r.data || [])).catch(() => setOpts([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);
  return (
    <div className="relative">
      <input className={inp} value={q} placeholder="CNAE ou descrição"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)} />
      {open && opts.length > 0 && (
        <div className="absolute z-20 bg-white border border-gray-200 rounded-lg mt-1 w-full max-h-48 overflow-y-auto shadow-lg">
          {opts.map((o) => (
            <button type="button" key={o.cnae} className="block w-full text-left px-3 py-2 text-xs hover:bg-gray-50"
              onMouseDown={() => { onPick(o); setQ(`${o.cnae_fmt} ${o.descricao}`); setOpen(false); }}>
              <b>{o.cnae_fmt}</b> — {o.descricao} <span className="text-gray-400">(grau {o.grau_risco})</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------- Modal de atividades ----------
function AtividadesModal({ estab, onFechar, embutido = false }: { estab: any; onFechar: () => void; embutido?: boolean }) {
  const [rows, setRows] = useState<any[]>([]);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  useEffect(() => {
    apiClient.get(`/estabelecimentos/${estab.id}/atividades`).then((r) => setRows(r.data || [])).catch(() => setRows([]));
  }, [estab.id]);
  const upd = (i: number, k: string, v: any) => setRows((l) => l.map((x, j) => j === i ? { ...x, [k]: v } : x));

  // ESPELHO DA REGRA DO BACKEND (Carolina, 25/10, item 2). A mesma atividade não pode ter dois
  // períodos cobrindo a mesma competência: ali não há o que comparar, há um quantitativo
  // duplicado, e o motor passa a depender da ordem das linhas no banco. Foi assim que a memória
  // saiu com o 4712-1/00 duas vezes, 50 e 50, ao lado do 4120-4/00 com 60 — e quem soma 100
  // contra 60 conclui que a preponderante apurada está errada, dentro do documento que a afirma.
  //
  // Atividades DIFERENTES na mesma competência continuam válidas, e têm de continuar: é
  // comparando os quantitativos delas que a preponderante se apura. A validação é por CNAE.
  const problema = (): string => {
    const uteis = rows.filter((r) => r.cnae || r.inicio);
    for (const r of uteis) {
      if (!r.cnae) return "Toda linha precisa de uma atividade (CNAE).";
      if (!r.inicio) return "Toda linha precisa de início.";
      if (r.fim && r.fim < r.inicio) return "Há uma atividade com fim anterior ao início.";
    }
    const porCnae: Record<string, any[]> = {};
    for (const r of uteis) {
      const c = String(r.cnae || "").replace(/\D/g, "");
      (porCnae[c] = porCnae[c] || []).push(r);
    }
    const mes = (d: string) => (d ? `${d.slice(5, 7)}/${d.slice(0, 4)}` : "em aberto");
    for (const [c, lista] of Object.entries(porCnae)) {
      const ord = [...lista].sort((a, b) => String(a.inicio).localeCompare(String(b.inicio)));
      for (let i = 0; i < ord.length - 1; i++) {
        if (!ord[i].fim || ord[i].fim >= ord[i + 1].inicio) {
          const fmt = `${c.slice(0, 4)}-${c.slice(4, 5)}/${c.slice(5)}`;
          return `O CNAE ${fmt} aparece em dois períodos que se sobrepõem: `
            + `${mes(ord[i].inicio)} a ${mes(ord[i].fim)} e ${mes(ord[i + 1].inicio)} a ${mes(ord[i + 1].fim)}. `
            + "Feche o período anterior antes de abrir o seguinte.";
        }
      }
    }
    return "";
  };

  const salvar = async () => {
    const p = problema();
    if (p) { setErro(p); return; }
    setSalvando(true); setErro("");
    try {
      await apiClient.put(`/estabelecimentos/${estab.id}/atividades`, rows.filter((r) => r.cnae && r.inicio).map((r) => ({
        cnae: (r.cnae || "").replace(/\D/g, "").slice(0, 7), descricao: r.descricao || null,
        quantitativo: r.quantitativo === "" || r.quantitativo == null ? null : Number(r.quantitativo),
        inicio: r.inicio, fim: r.fim || null,
      })));
      onFechar();
    } catch (e: any) { setErro(e?.response?.data?.detail || "Não foi possível salvar."); }
    finally { setSalvando(false); }
  };
  return (
    <div className={embutido ? "" : "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"}>
      <div className={embutido
            ? "bg-white rounded-xl border border-gray-100 p-5"
            : "bg-white rounded-2xl p-6 w-full max-w-3xl shadow-xl max-h-[90vh] overflow-y-auto"}>
        {!embutido && (
        <h2 className="text-lg font-bold text-gray-900">Atividades — {estab.nome}</h2>
        )}
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-[11px] text-amber-800 my-3">
          <b>Quem conta:</b> empregados CLT (inclui aprendiz) e trabalhadores avulsos.
          <b> Não contam:</b> contribuintes individuais (sócios/diretores sem vínculo, autônomos), estagiários, e terceirizados (contam na folha do prestador).
        </div>
        <p className="text-[11px] text-gray-400 mb-2">
          A preponderante é a atividade com maior número de trabalhadores, apurada mês a mês. Uma linha nova só quando a composição muda.
        </p>
        <div className="grid grid-cols-12 gap-2 text-[11px] text-gray-500 font-medium px-1">
          <div className="col-span-5">Atividade (CNAE)</div><div className="col-span-2">Nº trab.</div>
          <div className="col-span-2">Início</div><div className="col-span-2">Fim</div><div className="col-span-1"></div>
        </div>
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-start">
            <div className="col-span-5"><CnaeAutocomplete value={r.cnae} onPick={(o) => { upd(i, "cnae", o.cnae); upd(i, "descricao", o.descricao); }} /></div>
            <input type="number" className={`${inp} col-span-2`} value={r.quantitativo ?? ""} onChange={(e) => upd(i, "quantitativo", e.target.value)} placeholder="nº" />
            <input type="month" className={`${inp} col-span-2`} value={r.inicio ? String(r.inicio).slice(0, 7) : ""} onChange={(e) => upd(i, "inicio", e.target.value ? `${e.target.value}-01` : "")} />
            <input type="month" className={`${inp} col-span-2`} value={r.fim ? String(r.fim).slice(0, 7) : ""} onChange={(e) => upd(i, "fim", e.target.value ? `${e.target.value}-01` : "")} />
            <button type="button" className="col-span-1 text-red-400 text-sm mt-2" onClick={() => setRows((l) => l.filter((_, j) => j !== i))}>✕</button>
          </div>
        ))}
        <button type="button" className="text-[11px] text-teal-700 hover:underline" onClick={() => setRows((l) => [...l, { cnae: "", descricao: "", quantitativo: "", inicio: "", fim: "" }])}>+ atividade</button>
        {erro && <p className="text-xs text-red-500 mt-2">{erro}</p>}
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onFechar} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancelar</button>
          <button onClick={salvar} disabled={salvando} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {salvando ? "Salvando…" : "Salvar atividades"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- Painel de enquadramento apurado (RF-0.155/série) ----------
const CRIT: Record<string, string> = { maior_quantitativo: "maior quantitativo", desempate_grau: "empate → grau", fila_conferencia: "—" };
function PainelModal({ estab, onFechar, embutido = false }: { estab: any; onFechar: () => void; embutido?: boolean }) {
  const qc = useQueryClient();
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [apurando, setApurando] = useState(false);
  // Conferência (item da revisão de 19/10, interface). O endpoint existia desde então e nenhuma
  // tela o chamava: a situação "conferido" aparecia na listagem, a memória se apoiava nela e o
  // motor revogava conferências ao mudar o número — e não havia como criar uma.
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [obs, setObs] = useState("");
  const [agindo, setAgindo] = useState(false);
  const [msgErro, setMsgErro] = useState("");
  const load = () => {
    setLoading(true);
    setSel(new Set<string>());   // a série muda de estado; seleção velha apontaria para o que já não vale
    apiClient.get(`/estabelecimentos/${estab.id}/enquadramento`).then((r) => setRows(r.data || [])).catch(() => setRows([])).finally(() => setLoading(false));
  };
  useEffect(load, [estab.id]);
  const apurar = async () => { setApurando(true); try { await apiClient.post(`/estabelecimentos/${estab.id}/apurar`); load(); } catch { /* */ } finally { setApurando(false); } };

  // Conferir é assinar embaixo de um número. Onde não há número — competência em fila por falta
  // de dado, ou afastada do RAT pelo regime — não há o que assinar, e a caixa nem aparece. O
  // backend recusa essas com 422; oferecer o clique para depois recusá-lo seria desenhar o erro.
  const conferivel = (r: any) => r.situacao === "apurado" || r.situacao === "conferido";
  const selecionaveis = rows.filter(conferivel).map((r) => String(r.competencia));
  const todasMarcadas = selecionaveis.length > 0 && selecionaveis.every((c) => sel.has(c));
  const alternar = (comp: string) => setSel((s) => {
    const n = new Set(s);
    if (n.has(comp)) n.delete(comp); else n.add(comp);
    return n;
  });
  // Quantas da seleção ganham assinatura e quantas perdem. Os dois botões dizem o número, porque
  // "conferir 12" e "conferir" pedem graus de atenção diferentes antes do clique.
  const selArr = Array.from(sel);
  const aConferir = selArr.filter((c) => !rows.find((r) => String(r.competencia) === c)?.conferido_por).length;
  const aRetirar = selArr.length - aConferir;

  const agir = async (conferindo: boolean) => {
    // Manda só o que de fato muda de estado. Enviando a seleção inteira, "Conferir 12" passaria
    // também pelas já conferidas e reescreveria o nome de quem assinou pelo de quem clicou — o
    // mesmo erro que a preservação de autoria do regime (048) existe para impedir. E o número no
    // botão deixaria de ser verdade.
    const alvo = selArr.filter((c) => {
      const r = rows.find((x) => String(x.competencia) === c);
      return conferindo ? !r?.conferido_por : !!r?.conferido_por;
    });
    if (alvo.length === 0) return;
    setAgindo(true); setMsgErro("");
    try {
      await apiClient.post(`/estabelecimentos/${estab.id}/${conferindo ? "conferir" : "desconferir"}`,
        { competencias: alvo, observacao: obs.trim() || null });
      setObs("");
      load();
      qc.invalidateQueries({ queryKey: ["estabelecimentos"] });   // a situação da listagem mudou
    } catch (e: any) {
      // A recusa NOMEIA as competências pendentes. Trocá-la por "não foi possível" devolveria ao
      // usuário a tarefa de descobrir qual das sessenta linhas impediu o ato.
      setMsgErro(e?.response?.data?.detail || "Não foi possível registrar a conferência.");
    } finally { setAgindo(false); }
  };
  // Os quatro estados (conferência, apurado, conferido, não auditada) particionam a série; esta
  // linha de resumo só destaca dois deles. 'semAplicado' NÃO é um quinto grupo: é subconjunto das
  // apuradas — as que o motor fechou e ainda não têm o RAT aplicado informado. Era contado como
  // "todas as apuradas", e foi assim que a tela afirmou que as 58 estavam sem o aplicado quando
  // uma tinha. Contador não presume: quem não tem o dado é quem tem o campo vazio.
  const emFila = rows.filter((r) => r.situacao === "conferencia").length;
  const naoAuditadas = rows.filter((r) => r.situacao === "nao_auditada").length;
  // RECORTE DA FILA, não das apuradas (Carolina, 24/10). Era `situacao === "apurado" &&
  // aliquota_aplicada == null`, e essa combinação deixou de existir: competência sem o aplicado
  // desdobrado não é apurada, porque a comparação não fecha. O que interessa agora é, dentro da
  // fila, quantas já têm o devido calculado e esperam só o que a empresa aplicou — é a ação que
  // destrava a maior parte da série de uma vez.
  const aguardandoAplicado = rows.filter(
    (r) => r.situacao === "conferencia" && !r.em_fila && r.aliquota_devida != null).length;
  const conferidas = rows.filter((r) => r.conferido_por).length;
  return (
    <div className={embutido ? "" : "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"}>
      <div className={embutido
            ? "bg-white rounded-xl border border-gray-100 p-5"
            : "bg-white rounded-2xl p-6 w-full max-w-5xl shadow-xl max-h-[90vh] overflow-y-auto"}>
        <div className="flex items-center justify-between">
          {!embutido && (
          <h2 className="text-lg font-bold text-gray-900">Enquadramento apurado — {estab.nome}</h2>
          )}
          <div className="flex gap-2">
            <button onClick={async () => {
              try {
                const r = await apiClient.get(`/estabelecimentos/${estab.id}/memoria`, { responseType: "blob" });
                const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
                window.open(url, "_blank");
              } catch (e: any) {
                // A recusa de emissão NOMEIA o que falta e em quais competências. Como a resposta
                // vem como blob, o corpo do erro também vem — e era descartado aqui, virando um
                // "não foi possível" genérico. Mensagem que não diz o que fazer não é mensagem.
                let msg = "Não foi possível gerar a memória.";
                try {
                  const corpo = e?.response?.data;
                  const txt = corpo instanceof Blob ? await corpo.text() : null;
                  const det = txt ? JSON.parse(txt)?.detail : e?.response?.data?.detail;
                  if (det) msg = det;
                } catch { /* corpo ilegível: fica a mensagem genérica */ }
                alert(msg);
              }
            }} className="text-xs border border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50">Memória (PDF)</button>
            <button onClick={apurar} disabled={apurando} className="text-xs bg-teal-600 text-white px-3 py-1.5 rounded-lg hover:bg-teal-700 disabled:opacity-50">{apurando ? "Apurando…" : "Reapurar"}</button>
          </div>
        </div>
        <p className="text-[11px] text-gray-400 mt-1 mb-3">
          Série mensal. Grau e RAT devido derivados da atividade preponderante (Anexo I).
          Divergência = aplicado − alíquota efetiva (RAT × FAP).{" "}
          {emFila > 0 && <span className="text-amber-600">{emFila} em conferência. </span>}
          {naoAuditadas > 0 && <span className="text-gray-500">{naoAuditadas} não auditada(s) quanto ao RAT. </span>}
          {aguardandoAplicado > 0 && <span className="text-sky-700">{aguardandoAplicado} aguardando o RAT base e o FAP aplicados. </span>}
          {conferidas > 0 && <span className="text-emerald-700">{conferidas} conferida(s) por pessoa.</span>}
        </p>
        {naoAuditadas > 0 && (
          <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-900">
            {rows.find((r) => r.motivo_inaplicavel)?.motivo_inaplicavel ||
              "O regime tributário afasta a apuração do RAT em parte do período."}
          </div>
        )}
        {/* Barra de conferência. Só aparece com seleção: dois botões permanentemente
            desabilitados no topo ensinam a ignorar aquele canto da tela. */}
        {sel.size > 0 && (
          <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-medium text-emerald-900 whitespace-nowrap">
                {sel.size} competência{sel.size > 1 ? "s" : ""} selecionada{sel.size > 1 ? "s" : ""}
              </span>
              <input className="flex-1 min-w-[180px] border border-emerald-200 rounded-lg px-2 py-1 text-xs"
                value={obs} onChange={(e) => setObs(e.target.value)}
                placeholder="Observação (opcional) — fica registrada no evento" />
              {aConferir > 0 && (
                <button onClick={() => agir(true)} disabled={agindo}
                  className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded-lg hover:bg-emerald-700 disabled:opacity-50 whitespace-nowrap">
                  {agindo ? "Registrando…" : `Conferir ${aConferir}`}
                </button>
              )}
              {aRetirar > 0 && (
                <button onClick={() => agir(false)} disabled={agindo}
                  className="text-xs border border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-white disabled:opacity-50 whitespace-nowrap">
                  {agindo ? "…" : `Retirar conferência de ${aRetirar}`}
                </button>
              )}
              <button type="button" onClick={() => setSel(new Set<string>())} className="text-[11px] text-gray-500 hover:underline">limpar</button>
            </div>
            <p className="text-[11px] text-emerald-800 mt-1.5">
              Conferir é ato de pessoa: ficam registrados o seu nome, a data e o valor sobre o qual
              você assinou. Se o número mudar depois, a conferência é revogada e o sistema diz o
              que mudou.
            </p>
          </div>
        )}
        {msgErro && (
          <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[11px] text-red-700">{msgErro}</div>
        )}
        {loading ? <div className="p-6 text-center text-gray-400 text-sm">Carregando…</div>
          : rows.length === 0 ? <div className="p-6 text-center text-gray-400 text-sm">Nada apurado. Cadastre atividades (com quantitativo) e FAP; a série aparece aqui.</div>
          : (
            <table className="w-full text-xs">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-500">
                <tr>
                  <th className="px-2 py-2 w-8">
                    <input type="checkbox" disabled={selecionaveis.length === 0} checked={todasMarcadas}
                      title={selecionaveis.length ? "Selecionar todas as competências que podem ser conferidas" : "Nenhuma competência desta série pode ser conferida"}
                      onChange={() => setSel(todasMarcadas ? new Set<string>() : new Set<string>(selecionaveis))} />
                  </th>
                  {["Comp.", "Preponderante", "Critério", "Grau", "Devido", "FAP", "Efetivo", "Aplicado", "Diverg.", "Situação"].map((h) => <th key={h} className="text-left px-2 py-2 font-medium">{h}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((r, i) => (
                  <tr key={i} className={sel.has(String(r.competencia)) ? "bg-emerald-50" : r.situacao === "conferencia" ? "bg-amber-50" : r.situacao === "nao_auditada" ? "bg-gray-100/70 text-gray-500" : r.situacao === "apurado" ? "bg-sky-50/40" : "hover:bg-gray-50"}>
                    <td className="px-2 py-1.5">
                      {conferivel(r) && (
                        <input type="checkbox" checked={sel.has(String(r.competencia))}
                          onChange={() => alternar(String(r.competencia))} />
                      )}
                    </td>
                    <td className="px-2 py-1.5 font-mono">{r.competencia?.slice(0, 7)}</td>
                    <td className="px-2 py-1.5 font-mono">{fmt.cnae(r.cnae_preponderante)}</td>
                    <td className="px-2 py-1.5 text-gray-500">{CRIT[r.criterio] || r.criterio || "—"}</td>
                    <td className="px-2 py-1.5">{r.grau_risco ?? "—"}</td>
                    <td className="px-2 py-1.5">{fmt.pct(r.aliquota_devida)}</td>
                    <td className="px-2 py-1.5">{fmt.num(r.fap, 4)}</td>
                    <td className="px-2 py-1.5">{fmt.pct(r.aliquota_efetiva)}</td>
                    <td className="px-2 py-1.5">{fmt.pct(r.aliquota_aplicada)}</td>
                    {/* A divergência só é AFIRMADA com o aplicado desdobrado. Sem isso o mesmo
                        número admite duas leituras opostas — uma dá crédito, a outra dá zero — e
                        imprimir uma delas aqui é escolher por quem assina. A coluna mostra "?" e
                        diz onde resolver, em vez de um número que parece apurado. */}
                    {r.divergencia_confirmada === false ? (
                      <td className="px-2 py-1.5 font-medium tabular-nums text-amber-700"
                        title="Divergência não confirmada: depende de informar o RAT base e o FAP aplicados.">?</td>
                    ) : (
                      <td className={`px-2 py-1.5 font-medium tabular-nums ${r.divergencia_pp > 0 ? "text-blue-700" : r.divergencia_pp < 0 ? "text-red-700" : "text-gray-400"}`} title={r.divergencia_pp > 0 ? "pagou a mais — crédito a recuperar" : r.divergencia_pp < 0 ? "pagou a menos — passivo a regularizar" : ""}>{fmt.pp(r.divergencia_pp)}</td>
                    )}
                    <td className="px-2 py-1.5">
                      <span className={SIT[r.situacao]?.cls || "text-gray-400"}
                        title={r.motivo_inaplicavel || r.motivo_fila || SIT[r.situacao]?.ajuda || ""}>
                        {r.situacao === "conferencia" ? "⚠ " : ""}{SIT[r.situacao]?.txt || "—"}
                      </span>
                      {r.conferido_por && (
                        <span className="block text-[11px] text-gray-500">
                          {r.conferido_por}{dataHoraBR(r.conferido_em) ? ` · ${dataHoraBR(r.conferido_em)}` : ""}
                        </span>
                      )}
                      {!r.conferido_por && r.revogado_de && (
                        <span className="block text-[11px] text-amber-700"
                          title={`O número mudou depois da conferência${dataHoraBR(r.revogado_em) ? `, em ${dataHoraBR(r.revogado_em)}` : ""}.`}>
                          conferência de {r.revogado_de} revogada
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        {/* A citação NÃO vem mais congelada na linha apurada. Vinha: a tela pegava a primeira
            linha que tivesse fundamentação e imprimia aquele texto como rodapé de uma série de
            vários anos — sem data, sem dizer de quando era. Agora pergunta à tabela versionada
            pela PRIMEIRA competência da série, e o rodapé diz em que data resolveu. Se a norma
            mudou dentro do período, quem mostra competência por competência é a memória. */}
        {/* Embutido, quem mostra a fundamentação é a página — e mostra TODAS as vigências que a
            série atravessa, não só a da primeira competência. Esta linha afirmava uma redação só
            sobre anos inteiros de competências (Carolina, 27/10, item 10). */}
        {!embutido && rows.length > 0 && rows[0].competencia && (
          <p className="text-[11px] text-gray-400 mt-3">
            Fundamentação vigente em {mesBR(rows[0].competencia)}, início da série
            <Fundamentacao campo="rat_devido" em={rows[0].competencia} />
          </p>
        )}
        {/* "Fechar" só existe enquanto isto é uma janela. Embutido na página do
            estabelecimento não há o que fechar, e o botão viraria um beco. */}
        {!embutido && (
          <div className="flex justify-end mt-4"><button onClick={onFechar} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Fechar</button></div>
        )}
      </div>
    </div>
  );
}

// ---------- RAT aplicado pela empresa (item 1) ----------
// O único número do enquadramento que o sistema não calcula. É o que a empresa usou na folha —
// a diferença entre ele e a alíquota efetiva é o achado. Nunca preencher automaticamente.
function RatAplicadoModal({ estab, onFechar, embutido = false }: { estab: any; onFechar: () => void; embutido?: boolean }) {
  const [rows, setRows] = useState<any[]>([]);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  useEffect(() => {
    apiClient.get(`/estabelecimentos/${estab.id}/rat-aplicado`).then((r) => setRows(r.data || [])).catch(() => setRows([]));
  }, [estab.id]);
  const upd = (i: number, k: string, v: any) => setRows((l) => l.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  const problema = (): string => {
    for (const r of rows) {
      if (!r.inicio) return "Toda linha precisa de início.";
      if (r.fim && r.fim < r.inicio) return "Há um período com fim anterior ao início.";
      const temRat = r.aliquota_rat !== "" && r.aliquota_rat != null;
      const temFap = r.fap_aplicado !== "" && r.fap_aplicado != null;
      if (temRat !== temFap)
        return "Informe a alíquota RAT e o FAP aplicados juntos — só um dos dois não diz qual origem causou a divergência.";
      if (!temRat && !r.sem_desdobramento)
        return "Informe a alíquota RAT (1, 2 ou 3) e o FAP aplicados no período.";
      if (temRat) {
        if (![1, 2, 3].includes(Number(r.aliquota_rat))) return "A alíquota RAT aplicada deve ser 1, 2 ou 3.";
        const f = Number(r.fap_aplicado);
        if (!(f >= 0.5 && f <= 2.0)) return `FAP aplicado ${r.fap_aplicado} fora da faixa 0,5000–2,0000.`;
      }
    }
    const ord = [...rows].sort((x, y) => String(x.inicio).localeCompare(String(y.inicio)));
    for (let i = 0; i < ord.length - 1; i++) {
      if (!ord[i].fim || ord[i].fim >= ord[i + 1].inicio) return "Há períodos sobrepostos. Feche o anterior antes de abrir o próximo.";
    }
    return "";
  };

  const salvar = async () => {
    const p = problema();
    if (p) { setErro(p); return; }
    setSalvando(true); setErro("");
    try {
      await apiClient.put(`/estabelecimentos/${estab.id}/rat-aplicado`, rows.map((r) => {
        const temRat = r.aliquota_rat !== "" && r.aliquota_rat != null;
        return {
          aliquota_rat: temRat ? Number(r.aliquota_rat) : null,
          fap_aplicado: temRat ? Number(r.fap_aplicado) : null,
          // só viaja na linha antiga, que ainda não foi desdobrada
          aliquota: temRat ? null : Number(r.aliquota),
          processo_rat: r.processo_rat || null, processo_fap: r.processo_fap || null,
          inicio: r.inicio, fim: r.fim || null,
        };
      }));
      onFechar();
    } catch (e: any) { setErro(e?.response?.data?.detail || "Não foi possível salvar."); }
    finally { setSalvando(false); }
  };

  const efetivaDe = (r: any) => {
    const temRat = r.aliquota_rat !== "" && r.aliquota_rat != null;
    const temFap = r.fap_aplicado !== "" && r.fap_aplicado != null;
    if (temRat && temFap) return Number(r.aliquota_rat) * Number(r.fap_aplicado);
    return r.sem_desdobramento && r.aliquota != null ? Number(r.aliquota) : null;
  };
  const pendentes = rows.filter((r) => r.sem_desdobramento && (r.aliquota_rat === "" || r.aliquota_rat == null)).length;

  return (
    <div className={embutido ? "" : "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"}>
      <div className={embutido
            ? "bg-white rounded-xl border border-gray-100 p-5"
            : "bg-white rounded-2xl p-6 w-full max-w-4xl shadow-xl max-h-[90vh] overflow-y-auto"}>
        {!embutido && (
        <h2 className="text-lg font-bold text-gray-900">RAT aplicado pela empresa — {estab.nome}</h2>
        )}
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-[11px] text-amber-800 my-3">
          Informe o que a empresa <b>efetivamente declarou</b>, como está no eSocial (evento S-1005):
          a <b>alíquota RAT</b> (<code>aliqRat</code>) e o <b>FAP</b> (<code>fap</code>). A alíquota efetiva
          é o produto dos dois — o próprio eSocial valida isso, então o erro nunca está no produto:
          está no grau ou no fator. Guardar os dois separados é o que permite dizer <b>qual dos dois</b>
          causou a divergência, e cada um se defende de um jeito diferente.
        </div>
        {pendentes > 0 && (
          <div className="rounded-lg bg-sky-50 border border-sky-200 px-3 py-2 text-[11px] text-sky-900 mb-3">
            {pendentes} período(s) foram informados antes do desdobramento e guardam só a alíquota efetiva.
            O sistema <b>não</b> infere o par — informe a alíquota RAT e o FAP para que a memória possa
            apontar a origem da divergência.
          </div>
        )}
        <div className="grid grid-cols-12 gap-2 text-[11px] text-gray-500 font-medium px-1">
          <div className="col-span-2">Alíquota RAT</div><div className="col-span-2">FAP aplicado</div>
          <div className="col-span-2">Efetiva</div><div className="col-span-2">Início</div>
          <div className="col-span-2">Fim</div><div className="col-span-2"></div>
        </div>
        {rows.length === 0 && <p className="text-xs text-gray-400 py-3">Nenhum período informado. As competências ficam como <b>apurado</b> até que o aplicado seja declarado.</p>}
        {rows.map((r, i) => (
          <div key={i} className="mb-3 pb-3 border-b border-gray-100 last:border-0">
            <div className="grid grid-cols-12 gap-2 items-start">
              <select className={`${inp} col-span-2`} value={r.aliquota_rat ?? ""}
                onChange={(e) => upd(i, "aliquota_rat", e.target.value)}>
                <option value="">—</option>
                <option value="1">1 — leve</option>
                <option value="2">2 — médio</option>
                <option value="3">3 — grave</option>
              </select>
              <input type="number" step="0.0001" min="0.5" max="2" className={`${inp} col-span-2`}
                value={r.fap_aplicado ?? ""} onChange={(e) => upd(i, "fap_aplicado", e.target.value)} placeholder="1,0000" />
              <div className={`${inp} col-span-2 bg-gray-50 border-gray-200 text-gray-600`}>
                {efetivaDe(r) != null ? fmt.pct(efetivaDe(r)) : "—"}
              </div>
              <input type="month" className={`${inp} col-span-2`} value={r.inicio ? String(r.inicio).slice(0, 7) : ""}
                onChange={(e) => upd(i, "inicio", e.target.value ? `${e.target.value}-01` : "")} />
              <input type="month" className={`${inp} col-span-2`} value={r.fim ? String(r.fim).slice(0, 7) : ""}
                onChange={(e) => upd(i, "fim", e.target.value ? `${e.target.value}-01` : "")} />
              <button type="button" className="col-span-2 text-red-400 text-sm mt-2" onClick={() => setRows((l) => l.filter((_, j) => j !== i))}>✕ remover</button>
            </div>
            {/* O leiaute do eSocial só aceita alíquota divergente da prevista se houver processo
                informado. Sem isso, o sistema apontaria achado onde existe decisão amparando. */}
            <div className="grid grid-cols-2 gap-2 mt-2">
              <input className={inp} value={r.processo_rat ?? ""} onChange={(e) => upd(i, "processo_rat", e.target.value)}
                placeholder="Processo adm./judicial do RAT (se houver)" />
              <input className={inp} value={r.processo_fap ?? ""} onChange={(e) => upd(i, "processo_fap", e.target.value)}
                placeholder="Processo adm./judicial do FAP (se houver)" />
            </div>
          </div>
        ))}
        <button type="button" className="text-[11px] text-teal-700 hover:underline"
          onClick={() => setRows((l) => [...l, { aliquota_rat: "", fap_aplicado: "", processo_rat: "", processo_fap: "", inicio: "", fim: "" }])}>+ adicionar período</button>
        <p className="text-[11px] text-gray-400 mt-2">
          Deixe o fim em branco no período que segue vigente. Informe processo apenas quando houver
          decisão amparando alíquota diversa da prevista — nessas competências a divergência deixa de
          ser apontada como achado.
        </p>
        {erro && <p className="text-xs text-red-500 mt-2">{erro}</p>}
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onFechar} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancelar</button>
          <button onClick={salvar} disabled={salvando} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {salvando ? "Salvando…" : "Salvar e reapurar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- FPAS por período (item 4) ----------
function FpasModal({ estab, onFechar, embutido = false }: { estab: any; onFechar: () => void; embutido?: boolean }) {
  const [rows, setRows] = useState<any[]>([]);
  const [opcoes, setOpcoes] = useState<any[]>([]);
  // Item 3: período novo nasce cobrindo a janela de apuração inteira. Nascendo com um mês só,
  // 59 das 60 competências ficariam sem FPAS informado, e nada avisaria o usuário.
  const [janela, setJanela] = useState<{ inicio: string | null; fim: string | null } | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  useEffect(() => {
    apiClient.get(`/estabelecimentos/${estab.id}/fpas`)
      .then((r) => { setRows(r.data?.periodos || []); setJanela(r.data?.janela_sugerida || null); })
      .catch(() => setRows([]));
    apiClient.get(`/empresas/opcoes/fpas`).then((r) => setOpcoes(r.data || [])).catch(() => setOpcoes([]));
  }, [estab.id]);
  const upd = (i: number, k: string, v: any) => setRows((l) => l.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  const problema = (): string => {
    for (const r of rows) if (!r.codigo_fpas || !r.inicio) return "Toda linha precisa de código FPAS e início.";
    const ord = [...rows].sort((x, y) => String(x.inicio).localeCompare(String(y.inicio)));
    for (let i = 0; i < ord.length - 1; i++) {
      if (!ord[i].fim || ord[i].fim >= ord[i + 1].inicio) return "Há períodos sobrepostos. Feche o anterior antes de abrir o próximo.";
    }
    return "";
  };

  const salvar = async () => {
    const p = problema();
    if (p) { setErro(p); return; }
    setSalvando(true); setErro("");
    try {
      await apiClient.put(`/estabelecimentos/${estab.id}/fpas`,
        rows.map((r) => ({ codigo_fpas: r.codigo_fpas, inicio: r.inicio, fim: r.fim || null })));
      onFechar();
    } catch (e: any) { setErro(e?.response?.data?.detail || "Não foi possível salvar."); }
    finally { setSalvando(false); }
  };

  return (
    <div className={embutido ? "" : "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"}>
      <div className={embutido
            ? "bg-white rounded-xl border border-gray-100 p-5"
            : "bg-white rounded-2xl p-6 w-full max-w-3xl shadow-xl max-h-[90vh] overflow-y-auto"}>
        {!embutido && (
        <h2 className="text-lg font-bold text-gray-900">FPAS — {estab.nome}</h2>
        )}
        <p className="text-[11px] text-gray-400 mt-1 mb-3">
          O FPAS determina a composição das contribuições a Terceiros. Como essa composição muda
          dentro da janela de apuração, o código é informado <b>por período</b>. Opções:
          <b> Anexo II</b> (códigos) c/c <b>Anexo III</b> (alíquotas) da IN RFB 2.110/2022 — o
          dropdown exibe os dois dados.
          <Fundamentacao campo="fpas" em={hojeISO()} />
        </p>
        <div className="grid grid-cols-12 gap-2 text-[11px] text-gray-500 font-medium px-1">
          <div className="col-span-6">Código FPAS</div><div className="col-span-2">Início</div>
          <div className="col-span-2">Fim</div><div className="col-span-2"></div>
        </div>
        {rows.length === 0 && <p className="text-xs text-gray-400 py-3">Nenhum período informado.</p>}
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-start">
            <select className={`${inp} col-span-6`} value={r.codigo_fpas || ""} onChange={(e) => upd(i, "codigo_fpas", e.target.value)}>
              <option value="">— selecione —</option>
              {opcoes.map((o) => (
                <option key={o.codigo} value={o.codigo}>{o.codigo} — {o.descricao} ({fmt.pct(o.aliquota_terceiros)})</option>
              ))}
            </select>
            <input type="month" className={`${inp} col-span-2`} value={r.inicio ? String(r.inicio).slice(0, 7) : ""}
              onChange={(e) => upd(i, "inicio", e.target.value ? `${e.target.value}-01` : "")} />
            <input type="month" className={`${inp} col-span-2`} value={r.fim ? String(r.fim).slice(0, 7) : ""}
              onChange={(e) => upd(i, "fim", e.target.value ? `${e.target.value}-01` : "")} />
            <button type="button" className="col-span-2 text-red-400 text-sm mt-2" onClick={() => setRows((l) => l.filter((_, j) => j !== i))}>✕</button>
          </div>
        ))}
        <button type="button" className="text-[11px] text-teal-700 hover:underline"
          onClick={() => setRows((l) => [...l, {
            codigo_fpas: "",
            inicio: l.length === 0 ? (janela?.inicio || "") : "",
            fim: l.length === 0 ? (janela?.fim || "") : "",
          }])}>+ adicionar período</button>
        <p className="text-[11px] text-gray-400 mt-2">
          A alíquota mostrada ao lado de cada código é a vigente na tabela de referência. O cálculo de
          Terceiros por competência depende de versionar essa tabela — está na fila, e até lá o FPAS
          fica registrado aqui sem produzir valor apurado.
        </p>
        {erro && <p className="text-xs text-red-500 mt-2">{erro}</p>}
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onFechar} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancelar</button>
          <button onClick={salvar} disabled={salvando} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {salvando ? "Salvando…" : "Salvar FPAS"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- Modal de estabelecimento ----------
function EstabModal({ form, setForm, onSalvar, onFechar, isPending, erro, embutido = false }: any) {
  const editando = !!form.id;
  const cnpjInvalido = form.tipo_estabelecimento === "CNPJ" && form.cnpj && !validaCnpj(form.cnpj);
  return (
    <div className={embutido ? "" : "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"}>
      <div className={embutido
            ? "bg-white rounded-xl border border-gray-100 p-5"
            : "bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto"}>
        <h2 className="text-lg font-bold text-gray-900 mb-4">{editando ? "Editar" : "Novo"} Estabelecimento</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><label className={lbl}>Código *</label><input className={inp} value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></div>
            <div><label className={lbl}>Nome *</label><input className={inp} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={lbl}>Natureza</label>
              <select className={inp} value={form.tipo_estabelecimento} onChange={(e) => setForm({ ...form, tipo_estabelecimento: e.target.value })}>
                {NATUREZAS.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div><label className={lbl}>Posição</label>
              <select className={inp} value={form.posicao} onChange={(e) => setForm({ ...form, posicao: e.target.value })}>
                {POSICOES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>
          {form.tipo_estabelecimento === "CNPJ" ? (
            <div><label className={lbl}>CNPJ *</label>
              <input className={`${inp} ${cnpjInvalido ? "border-red-400" : ""}`} value={maskCnpj(form.cnpj)} maxLength={18}
                onChange={(e) => setForm({ ...form, cnpj: e.target.value.replace(/\D/g, "").slice(0, 14) })} placeholder="00.000.000/0000-00" />
              {cnpjInvalido && <p className="text-[11px] text-red-500 mt-1">CNPJ inválido (dígito verificador).</p>}
            </div>
          ) : (
            <div><label className={lbl}>{form.tipo_estabelecimento === "CNO" ? "Matrícula CNO *" : "Identificador (CAEPF)"}
              {form.tipo_estabelecimento === "CNO" && <Fundamentacao campo="obra_cno" em={hojeISO()} />}</label>
              <input className={inp} value={form.identificador} onChange={(e) => setForm({ ...form, identificador: e.target.value })} /></div>
          )}
          <div className="grid grid-cols-3 gap-3">
            <div><label className={lbl}>Abertura *</label><input type="date" className={inp} value={form.data_abertura || ""} onChange={(e) => setForm({ ...form, data_abertura: e.target.value })} /></div>
            <div><label className={lbl}>Encerramento</label><input type="date" className={inp} value={form.data_encerramento || ""} onChange={(e) => setForm({ ...form, data_encerramento: e.target.value })} /></div>
            <div><label className={lbl}>Status</label>
              <select className={inp} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {STATUS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          {/* Item 5: endereço ESTRUTURADO, igual à tela da empresa. O campo único impedia o
              preenchimento por CEP — e o endereço do estabelecimento entra na memória. */}
          <div className="grid grid-cols-6 gap-3">
            <div className="col-span-2"><label className={lbl}>CEP</label>
              <input className={inp} value={maskCep(form.cep || "")} maxLength={9} inputMode="numeric" placeholder="00000-000"
                onChange={(e) => { const v = maskCep(e.target.value); setForm({ ...form, cep: v }); if (v.replace(/\D/g, "").length === 8) buscarCep(v, form, setForm); }}
                onBlur={(e) => buscarCep(e.target.value, form, setForm)} />
            </div>
            <div className="col-span-4"><label className={lbl}>Logradouro</label><input className={inp} value={form.endereco || ""} onChange={(e) => setForm({ ...form, endereco: e.target.value })} /></div>
            <div className="col-span-2"><label className={lbl}>Número</label><input className={inp} value={form.numero || ""} onChange={(e) => setForm({ ...form, numero: e.target.value })} /></div>
            <div className="col-span-4"><label className={lbl}>Complemento</label><input className={inp} value={form.complemento || ""} onChange={(e) => setForm({ ...form, complemento: e.target.value })} /></div>
            <div className="col-span-3"><label className={lbl}>Bairro</label><input className={inp} value={form.bairro || ""} onChange={(e) => setForm({ ...form, bairro: e.target.value })} /></div>
            <div className="col-span-2"><label className={lbl}>Cidade</label><input className={inp} value={form.cidade || ""} onChange={(e) => setForm({ ...form, cidade: e.target.value })} /></div>
            <div><label className={lbl}>UF</label>
              <select className={inp} value={form.uf || ""} onChange={(e) => setForm({ ...form, uf: e.target.value })}>
                <option value="">—</option>
                {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
          </div>
          {/* Enquadramento apurado — visível e NÃO editável. Apresentado como VALOR e não como
              caixa de entrada: a distinção entre "isto você preenche" e "isto o sistema calculou"
              precisa ser evidente sem ler a legenda do cadeado. */}
          {editando && (
            <div className="border-t border-gray-100 pt-3">
              <div className="flex items-baseline justify-between">
                <label className={lbl}>Enquadramento apurado<Fundamentacao campo="rat_devido" em={hojeISO()} /></label>
                <span className="text-[11px] text-gray-400">
                  {form.enquadramento_atual?.competencia ? `competência ${mesBR(form.enquadramento_atual.competencia)}` : "sem série apurada"}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 mt-2">
                <div>
                  <span className={derivLabel}>Grau de risco</span>
                  <div className={derivVal}>{form.enquadramento_atual?.grau_risco
                    ? <>{form.enquadramento_atual.grau_risco}<span className="text-sm font-normal text-gray-500"> {form.enquadramento_atual.grau_label}</span></> : "—"}</div>
                </div>
                <div>
                  <span className={derivLabel}>RAT devido</span>
                  <div className={derivVal}>{fmt.pct(form.enquadramento_atual?.aliquota_devida)}</div>
                </div>
                <div>
                  <span className={derivLabel}>Situação</span>
                  <div className={`${derivVal} ${SIT[form.enquadramento_atual?.situacao]?.cls || ""}`}>
                    <span className="text-base">{SIT[form.enquadramento_atual?.situacao]?.txt || "—"}</span>
                  </div>
                </div>
              </div>
              <p className="text-[11px] text-gray-400 mt-2">
                🔒 Derivado da atividade preponderante (RN-20) — não se escolhe aqui. Para mudar,
                altere as atividades.
              </p>
            </div>
          )}
          {!editando && <p className="text-[11px] text-gray-400">O grau de risco e o RAT devido são derivados da atividade preponderante (não se escolhem aqui). Cadastre as atividades após salvar.</p>}
        </div>
        {erro && <p className="text-xs text-red-500 mt-3">{erro}</p>}
        <div className="flex gap-3 mt-5">
          <button onClick={onFechar} className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50">Cancelar</button>
          <button onClick={onSalvar} disabled={!form.codigo || !form.nome || isPending || cnpjInvalido}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
            {isPending ? "Salvando…" : (editando ? "Salvar" : "Cadastrar")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- FAP publicado, por ano (item 5 da etapa C) ----------
// Era um modal escrito DENTRO do componente da lista, usando o estado dela (fapValores,
// fapSalvando). Por isso nao podia ser aproveitado pela pagina do estabelecimento, e o bloco
// "FAP publicado" ficou vazio na etapa B, anunciando que entraria depois. Agora e componente,
// com estado proprio, e serve aos dois lugares.
//
// Em leitura mostra os anos como a folha pede, com o nao informado destacado: e o que trava
// competencias em conferencia, e some num campo em branco dentro de um formulario.
const ANOS_FAP = [2021, 2022, 2023, 2024, 2025, 2026];

function FapBloco({ estab, embutido = false, onFechar, editando = false, onEditar }: {
  estab: any; embutido?: boolean; onFechar?: () => void; editando?: boolean; onEditar?: () => void;
}) {
  const [valores, setValores] = useState<Record<number, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = () => {
    apiClient.get(`/estabelecimentos/${estab.id}/fap`).then((r) => {
      const m: Record<number, string> = {};
      (r.data || []).forEach((x: any) => { m[x.ano] = fmt.num(x.fap, 4); });
      setValores(m);
    }).catch(() => setValores({}));
  };
  useEffect(carregar, [estab.id]);

  const salvar = async () => {
    setSalvando(true); setErro("");
    try {
      const faps = ANOS_FAP
        .filter((a) => valores[a] !== undefined && valores[a] !== "")
        .map((a) => ({ ano: a, fap: Number(String(valores[a]).replace(".", "").replace(",", ".")) }));
      await apiClient.put(`/estabelecimentos/${estab.id}/fap`, faps);
      onFechar?.();
    } catch { setErro("Não foi possível salvar o FAP."); } finally { setSalvando(false); }
  };

  const campos = (
    <>
      <p className="text-xs text-gray-500 mb-3">
        O cálculo usa o FAP de cada ano. Campo vazio não é 1,0 — fica em branco e vai à conferência.
      </p>
      <div className="space-y-2">
        {ANOS_FAP.map((ano) => (
          <div key={ano} className="flex items-center gap-3">
            <label className="w-16 text-sm text-gray-600">{ano}</label>
            <input type="text" inputMode="decimal"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm tabular-nums"
              value={valores[ano] ?? ""}
              onChange={(ev) => setValores((v) => ({ ...v, [ano]: ev.target.value }))}
              onBlur={(ev) => {
                // Quatro casas, com vírgula: é assim que a norma define o FAP.
                const n = Number(String(ev.target.value).replace(",", "."));
                setValores((v) => ({ ...v, [ano]: ev.target.value === "" || Number.isNaN(n) ? "" : fmt.num(n, 4) }));
              }}
              placeholder="não informado" />
          </div>
        ))}
      </div>
      {erro && <p className="text-xs text-red-600 mt-2">{erro}</p>}
      <div className="flex justify-end gap-2 mt-5">
        <button onClick={() => { carregar(); onFechar?.(); }} className="px-4 py-2 text-sm text-gray-600">Cancelar</button>
        <button onClick={salvar} disabled={salvando}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
          {salvando ? "Salvando…" : "Salvar FAP"}
        </button>
      </div>
    </>
  );

  // Como bloco da página: leitura por padrão, formulário quando o "editar" pedir.
  if (embutido) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 p-5">
        {editando ? campos : (
          <div className="grid grid-cols-3 gap-2">
            {ANOS_FAP.map((ano) => {
              const v = valores[ano];
              return (
                <div key={ano}
                  className={`rounded-lg border px-3 py-2 text-center ${v ? "border-gray-200" : "border-amber-300 bg-amber-50"}`}>
                  <p className="text-[11px] text-gray-500">{ano}</p>
                  <p className={`text-sm tabular-nums ${v ? "text-gray-800" : "text-amber-800"}`}>
                    {v || "não informado"}
                  </p>
                </div>
              );
            })}
          </div>
        )}
        {!editando && onEditar === undefined && null}
      </div>
    );
  }

  // Como janela, enquanto a lista antiga ainda existir.
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-bold text-gray-900">
          FAP por ano — {estab.nome}<Fundamentacao campo="fap_publicado" em={hojeISO()} />
        </h2>
        {campos}
      </div>
    </div>
  );
}

export function Estabelecimentos() {
  const qc = useQueryClient();
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState<any>(FORM_VAZIO);
  const [erro, setErro] = useState("");
  const navegar = useNavigate();
  const [busca, setBusca] = useState("");
  const [ordem, setOrdem] = useState("pendencia");
  const [filtro, setFiltro] = useState("todos");

  const { data: estabs = [], isLoading } = useQuery({
    queryKey: ["estabelecimentos"],
    queryFn: () => apiClient.get("/estabelecimentos/").then((r) => r.data),
  });

  // FILTROS POR NATUREZA E POR PENDENCIA (itens 3 e 4). A busca e a ordenacao continuam no
  // cliente: a lista de um escritorio nao justifica paginar no servidor.
  const pendente = (e: any) => ((e.resumo?.o_que_falta || []).length > 0);
  const encerrado = (e: any) => String(e.status || "").toLowerCase().startsWith("encerrad");

  const casaFiltro = (e: any, f: string) =>
    f === "todos" ? true
    : f === "pendencia" ? pendente(e)
    : f === "encerrados" ? encerrado(e)
    : String(e.posicao || "").toLowerCase() === f;

  const contaFiltro = (f: string) => estabs.filter((e: any) => casaFiltro(e, f)).length;

  const visiveis = (() => {
    const q = busca.trim().toLowerCase();
    const filtrados = estabs
      .filter((e: any) => casaFiltro(e, filtro))
      .filter((e: any) => !q || [e.nome, e.cnpj, e.identificador]
        .some((v: any) => String(v || "").toLowerCase().includes(q)));
    // COM PENDENCIA PRIMEIRO, por padrao: "quem abre a lista vê de cara onde trabalhar".
    filtrados.sort((a: any, b: any) =>
      ordem === "nome"
        ? String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR")
        : (Number(pendente(b)) - Number(pendente(a)))
          || String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"));
    return filtrados;
  })();

  // O rótulo da janela no cabeçalho da coluna, quando todos concordam. Estabelecimentos com
  // janelas diferentes não ganham um período único no título — seria afirmar o de um sobre todos.
  const janelaRotulo: string = (() => {
    // Set<string> explícito: montado a partir de um map sobre `any`, o Set sai sem tipo e o
    // elemento vira `unknown`, que o JSX não aceita renderizar.
    const js = Array.from(new Set<string>(
      estabs
        .map((e: any) => e.resumo?.janela)
        .filter(Boolean)
        .map((j: any) => `${fmt.competencia(j.inicio)} a ${fmt.competencia(j.fim)}`)
    ));
    return js.length === 1 ? js[0] : "";
  })();

  const salvar = useMutation({
    mutationFn: (d: any) => d.id ? apiClient.put(`/estabelecimentos/${d.id}`, d) : apiClient.post("/estabelecimentos/", d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["estabelecimentos"] }); setModal(false); setForm(FORM_VAZIO); },
    onError: (e: any) => setErro(e?.response?.data?.detail || "Tente novamente."),
  });

  const onSalvar = () => {
    setErro("");
    const p: any = { ...form };
    ["cnpj", "identificador", "endereco", "cep", "numero", "complemento", "bairro", "cidade", "uf", "data_encerramento"]
      .forEach((k) => { if (!p[k]) p[k] = null; });
    delete p.enquadramento_atual;   // bloco somente leitura; não é campo do cadastro
    delete p.completude;            // indicador calculado, não é campo do cadastro
    if (!p.id) delete p.id;
    salvar.mutate(p);
  };


  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Estabelecimentos</h1>
          <p className="text-sm text-gray-500 mt-1">
            Matriz, filiais e obras. O enquadramento pertence a cada estabelecimento.
          </p>
        </div>
        <button onClick={() => { setForm(FORM_VAZIO); setErro(""); setModal(true); }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + Novo estabelecimento
        </button>
      </div>

      {/* A LISTA E UM INDICE, NAO UMA PLANILHA (Carolina, etapa C, itens 1 a 4).
          "A lista só responde a três perguntas: quais estabelecimentos existem, em que estado
          está a janela de cada um e o que falta preencher. Tudo o mais fica na página."

          Sairam daqui codigo, grau, RAT devido, efetiva, divergencia de um mes, abertura, as
          etiquetas At·FAP·RAT·FPAS e a fileira de seis acoes. Nada disso sumiu do sistema: esta
          na pagina do estabelecimento, que abre ao clicar na linha. */}
      <div className="flex flex-wrap items-center gap-3">
        <input className="flex-1 min-w-[260px] border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={busca} onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por nome, CNPJ ou CNO…" />
        <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={ordem}
          onChange={(e) => setOrdem(e.target.value)}>
          <option value="pendencia">Ordenar: com pendência primeiro</option>
          <option value="nome">Ordenar por nome</option>
        </select>
      </div>

      {/* Os filtros fazem o trabalho que a rolagem lateral não fazia: com quarenta obras, achar
          o que falta preencher deixa de depender de varrer a tela. */}
      <div className="flex flex-wrap gap-2">
        {FILTROS.map(([chave, rotulo]) => (
          <button key={chave} onClick={() => setFiltro(chave)}
            className={`text-xs rounded-full px-3 py-1.5 border ${filtro === chave
              ? "bg-gray-900 text-white border-gray-900"
              : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}>
            {rotulo} · {contaFiltro(chave)}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        {isLoading ? <div className="p-8 text-center text-gray-400">Carregando…</div>
          : estabs.length === 0 ? <div className="p-8 text-center text-gray-400">Nenhum estabelecimento.</div>
          : visiveis.length === 0 ? <div className="p-8 text-center text-gray-400">Nenhum estabelecimento neste filtro.</div>
          : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr className="text-[10px] uppercase tracking-wide text-gray-500 text-left">
                  <th className="px-4 py-3">Estabelecimento</th>
                  <th className="px-3">CNPJ / CNO</th>
                  <th className="px-3">Janela{janelaRotulo && <span className="normal-case"> · {janelaRotulo}</span>}</th>
                  <th className="px-3">O que falta</th>
                  <th className="px-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {visiveis.map((e: any) => {
                  const res = e.resumo;
                  const est = res?.estado;
                  const pos = res?.posicao;
                  const falta: any[] = res?.o_que_falta || [];
                  const temPosicao = pos && (pos.com_credito + pos.com_debito + pos.sem_divergencia) > 0;
                  return (
                    <tr key={e.id} className="hover:bg-gray-50 cursor-pointer align-top"
                      onClick={() => navegar(`/estabelecimentos/${e.id}`)}>
                      <td className="px-4 py-4">
                        <p className="font-bold text-gray-900">{e.nome}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          <span className="inline-block bg-gray-100 rounded px-1.5 py-0.5 mr-2 uppercase tracking-wide text-[10px] font-semibold">
                            {e.posicao || "—"}
                          </span>
                          {e.cidade ? `${e.cidade}/${e.uf || ""}` : ""}{e.status ? ` · ${e.status}` : ""}
                        </p>
                      </td>
                      <td className="px-3 py-4 font-mono text-xs text-gray-600">
                        {e.cnpj ? fmt.cnpj(e.cnpj) : (e.identificador ? `CNO ${e.identificador}` : "—")}
                      </td>
                      <td className="px-3 py-4 text-xs">
                        {!est ? <span className="text-gray-400">série não apurada</span> : (
                          <>
                            <p className="text-gray-700">
                              <b>{est.apuradas} apuradas</b> · {est.em_conferencia} em conferência ·{" "}
                              {est.conferidas} conferidas
                            </p>
                            {/* A COLUNA RESUME O PERIODO INTEIRO. Ela substitui a divergência de um
                                mês só, que na lista parecia ser a do estabelecimento. */}
                            {temPosicao ? (
                              <p className="mt-1 text-gray-700">
                                competências: <b className="text-indigo-700">{pos.com_credito} com crédito</b> ·{" "}
                                <b className="text-red-700">{pos.com_debito} com débito</b> ·{" "}
                                {pos.sem_divergencia} sem divergência
                              </p>
                            ) : (
                              <p className="mt-1 text-gray-400">sem posição — nada apurado</p>
                            )}
                          </>
                        )}
                      </td>
                      <td className="px-3 py-4">
                        {/* O QUE FALTA, EM PALAVRAS. Eram as etiquetas cifradas At · FAP · RAT ·
                            FPAS, que só diziam alguma coisa a quem já sabia o que significavam. */}
                        {falta.length === 0 ? (
                          <span className="text-xs text-emerald-700">✓ completo</span>
                        ) : (
                          <span className="inline-block text-xs rounded-md border border-amber-300 bg-amber-50 text-amber-900 px-2 py-1">
                            {falta.map((f) => f.motivo).join(" · ")}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-4 text-gray-300">›</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
      </div>

      {modal && <EstabModal form={form} setForm={setForm} onSalvar={onSalvar} onFechar={() => { setModal(false); setForm(FORM_VAZIO); }} isPending={salvar.isPending} erro={erro} />}
      {/* ITEM 11: as janelas que viraram blocos não são mais abertas daqui. Os componentes
          continuam existindo — a página do estabelecimento os usa embutidos —, o que saiu foi a
          abertura como janela sobre a lista, que era o empilhamento que a revisão eliminou.
          Fica só o EstabModal, que é o cadastro de um estabelecimento novo e nunca virou bloco. */}
    </div>
  );
}


// ==============================================================================================
// A PÁGINA DO ESTABELECIMENTO (revisão da Carolina, 27/10 — etapa B)
//
// "Tudo de um estabelecimento num lugar só. Abre ao clicar na linha da lista. No topo, o resumo
// da janela e o que falta. Embaixo, os blocos na ordem em que o cálculo depende deles."
//
// POR QUE A ORDEM DOS BLOCOS É ESTA: quem é o estabelecimento, que atividades tem, qual FAP foi
// publicado, o que a empresa aplicou, e só então o resultado. Quem lê de cima para baixo entende
// de onde veio cada número — era o que a sequência de janelas empilhadas impedia, porque não
// havia como ver duas ao mesmo tempo.
//
// OS BLOCOS SÃO OS MESMOS COMPONENTES das antigas janelas, com `embutido`: o conteúdo e a lógica
// de gravação já estavam certos e revisados; o que mudou foi a moldura. Reescrevê-los do zero
// significaria reintroduzir defeitos que já foram corrigidos uma vez.
// ==============================================================================================
export function EstabelecimentoPagina() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: estabs } = useQuery({
    queryKey: ["estabelecimentos"],
    queryFn: async () => (await apiClient.get("/estabelecimentos/")).data,
  });
  const estab = (estabs || []).find((e: any) => String(e.id) === String(id));

  // O resumo vem do backend, das mesmas funções que a memória de cálculo usa (etapa A). A tela
  // não soma nada por conta própria: é o que garante que este topo, a lista e o documento nunca
  // mostrem números diferentes.
  const { data: resumo } = useQuery({
    enabled: !!id,
    queryKey: ["estab-resumo", id],
    queryFn: async () => (await apiClient.get(`/estabelecimentos/${id}/enquadramento/resumo`)).data,
  });

  const { data: ativs } = useQuery({
    enabled: !!id,
    queryKey: ["estab-ativ", id],
    queryFn: async () => (await apiClient.get(`/estabelecimentos/${id}/atividades`)).data,
  });
  const { data: ratApl } = useQuery({
    enabled: !!id,
    queryKey: ["estab-rat", id],
    queryFn: async () => (await apiClient.get(`/estabelecimentos/${id}/rat-aplicado`)).data,
  });

  // A série mensal e a conferência ficam a um clique, fechadas por padrão (item 7).
  const [serieAberta, setSerieAberta] = useState(false);

  const ABAS = [
    ["identificacao", "Identificação"],
    ["atividades", "Atividades"],
    ["fap", "FAP publicado"],
    ["rat", "RAT aplicado"],
    ["enquadramento", "Enquadramento"],
    ["fpas", "FPAS e Terceiros"],
  ] as const;

  // ROLAGEM ÚNICA: a aba não troca de conteúdo, leva até o bloco. Todos continuam visíveis, que é
  // o ponto da mudança — esconder blocos atrás de abas recriaria a janela empilhada com outro nome.
  const irPara = (ancora: string) =>
    document.getElementById(`bloco-${ancora}`)?.scrollIntoView({ behavior: "smooth", block: "start" });

  if (!estab) {
    return (
      <div className="p-6">
        <button onClick={() => navigate("/estabelecimentos")} className="text-sm text-indigo-700 hover:underline">
          ← Estabelecimentos
        </button>
        <p className="text-sm text-gray-500 mt-4">Carregando o estabelecimento…</p>
      </div>
    );
  }

  const r = resumo || {};
  const est = r.estado || {};
  const pos = r.posicao || {};
  const falta: any[] = r.o_que_falta || [];
  const janela = r.janela || {};
  const periodo = janela.inicio && janela.fim
    ? `${fmt.competencia(janela.inicio)} a ${fmt.competencia(janela.fim)}`
    : "sem competências apuradas";

  const Bloco = ({ ancora, titulo, children, acao }: {
    ancora: string; titulo: string; children: any; acao?: any;
  }) => (
    <section id={`bloco-${ancora}`} className="scroll-mt-24 mb-4">
      <div className="flex items-baseline justify-between mb-2">
        <h2 className="text-sm font-bold text-gray-800">{titulo}</h2>
        {acao}
      </div>
      {children}
    </section>
  );

  // ITEM 6: OS BLOCOS ABREM EM LEITURA. Ela: "hoje a página é um formulário inteiro aberto, o que
  // tira a visão ampla e deixa alterar dado sem querer." Em leitura o bloco mostra o que está
  // valendo; "editar" troca aquele bloco — e só aquele — pelo formulário, que continua sendo o
  // componente já revisado da janela antiga.
  const [editando, setEditando] = useState<string | null>(null);
  const BotaoEditar = ({ bloco }: { bloco: string }) => (
    <button onClick={() => setEditando((v) => (v === bloco ? null : bloco))}
      className="text-xs text-indigo-700 hover:underline">
      {editando === bloco ? "fechar" : "editar"}
    </button>
  );

  // O cartão de leitura de um bloco que ainda não tem resumo próprio: diz o que há, sem abrir
  // formulário. Some assim que o bloco ganhar a sua própria leitura.
  const Leitura = ({ children }: { children: any }) => (
    <div className="bg-white rounded-xl border border-gray-100 p-5 text-xs text-gray-600">{children}</div>
  );

  return (
    <div className="p-6 max-w-6xl">
      <button onClick={() => navigate("/estabelecimentos")} className="text-sm text-indigo-700 hover:underline">
        ← Estabelecimentos
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mt-2">{estab.nome || estab.codigo}</h1>
      <p className="text-xs text-gray-500 mt-1">
        <span className="inline-block bg-gray-100 text-gray-700 rounded px-1.5 py-0.5 mr-2 uppercase tracking-wide text-[10px] font-semibold">
          {estab.posicao || "—"}
        </span>
        <span className="font-mono">{estab.cnpj ? fmt.cnpj(estab.cnpj) : (estab.identificador || "—")}</span>
        {estab.cidade ? ` · ${estab.cidade}/${estab.uf || ""}` : ""}
        {estab.data_abertura ? ` · ativa desde ${fmt.data(estab.data_abertura)}` : ""}
      </p>

      {/* O TOPO RESPONDE TRÊS COISAS antes de qualquer bloco: qual é a janela, como ela está, e o
          que falta preencher. "O usuário não precisa adivinhar por que duas competências estão em
          conferência." */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 mb-5">
        <div className="border border-gray-200 rounded-xl p-4">
          <p className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">Janela · {periodo}</p>
          <p className="text-sm text-gray-800 mt-1">
            <b>{est.apuradas ?? 0} apuradas</b> · {est.em_conferencia ?? 0} em conferência ·{" "}
            {est.conferidas ?? 0} conferidas
            {est.nao_auditadas ? ` · ${est.nao_auditadas} não auditadas` : ""}
          </p>
        </div>
        <div className="border border-gray-200 rounded-xl p-4">
          <p className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">Posição na janela — em competências</p>
          {(pos.total ?? 0) === 0 || (pos.com_credito + pos.com_debito + pos.sem_divergencia) === 0 ? (
            <p className="text-sm text-gray-500 mt-1">sem posição — nada apurado</p>
          ) : (
            <p className="text-sm text-gray-800 mt-1">
              <b className="text-indigo-700">{pos.com_credito} com crédito</b> ·{" "}
              <b className="text-red-700">{pos.com_debito} com débito</b> ·{" "}
              {pos.sem_divergencia} sem divergência
            </p>
          )}
        </div>
        <div className={`rounded-xl p-4 border ${falta.length ? "border-amber-300 bg-amber-50" : "border-gray-200"}`}>
          <p className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">O que falta</p>
          {falta.length === 0 ? (
            <p className="text-sm text-emerald-700 mt-1">✓ completo</p>
          ) : (
            falta.map((f, i) => (
              <p key={i} className="text-sm text-amber-900 mt-1 leading-snug">{f.texto}</p>
            ))
          )}
        </div>
      </div>

      {/* As abas ficam fixas e só levam ao bloco. O ponto marca a aba que tem pendência. */}
      <div className="sticky top-0 z-20 bg-white border-b border-gray-200 flex gap-4 overflow-x-auto mb-4 py-2">
        {ABAS.map(([k, rotulo]) => {
          // A aba de FAP ganha o ponto quando a pendência cita FAP; a de atividades idem. O texto
          // do motivo é o mesmo que o topo exibe — não há segunda regra decidindo isso.
          const pendente = falta.some((f) => (f.motivo || "").toLowerCase().includes(
            k === "fap" ? "fap" : k === "atividades" ? "atividade" : k === "rat" ? "aplicado" : "\u0000"));
          return (
            <button key={k} onClick={() => irPara(k)}
              className="text-sm text-gray-600 hover:text-gray-900 whitespace-nowrap">
              {rotulo}{pendente && <span className="ml-1 text-amber-500">•</span>}
            </button>
          );
        })}
      </div>

      <Bloco ancora="identificacao" titulo="Identificação">
        <div className="bg-white rounded-xl border border-gray-100 p-5 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><p className="text-[11px] text-gray-500">Natureza</p><p>{fmt.natureza(estab.posicao, estab.tipo_estabelecimento)}</p></div>
          <div><p className="text-[11px] text-gray-500">CNPJ / CNO</p><p className="font-mono">{estab.cnpj ? fmt.cnpj(estab.cnpj) : (estab.identificador || "—")}</p></div>
          <div><p className="text-[11px] text-gray-500">Abertura</p><p>{estab.data_abertura ? fmt.data(estab.data_abertura) : "—"}</p></div>
          <div><p className="text-[11px] text-gray-500">Situação</p><p>{estab.status || "—"}</p></div>
        </div>
      </Bloco>

      {/* Os quatro blocos abaixo são as antigas janelas, agora embutidas. O conteúdo e a gravação
          são os mesmos; some só a moldura flutuante. */}
      <Bloco ancora="atividades" titulo="Atividades — quantitativo de segurados empregados e avulsos"
        acao={<BotaoEditar bloco="atividades" />}>
        {editando === "atividades" ? (
          <AtividadesModal estab={estab} onFechar={() => setEditando(null)} embutido />
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 p-5">
            {(ativs || []).length === 0 ? (
              <p className="text-xs text-gray-500">Nenhuma atividade declarada.</p>
            ) : (
              <>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wide text-gray-500 text-left">
                      <th className="py-1">CNAE</th><th>Descrição</th><th>Nº trab.</th><th>Vigência</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(ativs || []).map((a: any, i: number) => (
                      <tr key={i} className="text-gray-700">
                        <td className="py-2 font-mono">{fmt.cnae(a.cnae)}</td>
                        <td className="pr-3">{a.descricao || "—"}</td>
                        <td>{a.quantitativo}</td>
                        <td>{fmt.competencia(a.inicio)} a {a.fim ? fmt.competencia(a.fim) : "vigente"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {/* A autoria fica na leitura, não dentro do formulário: é informação de quem lê,
                    não de quem edita. */}
                {(ativs || []).some((a: any) => a.declarado_por) && (
                  <p className="text-[11px] text-gray-500 mt-3">
                    Declarado por {(ativs || []).find((a: any) => a.declarado_por)?.declarado_por}.
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </Bloco>

      {/* ITEM 5: O FAP SAIU DA LISTA e virou bloco. Em leitura, um cartão por ano, com o não
          informado destacado — é ele que trava competências em conferência, e num campo em branco
          dentro de um formulário isso não se vê. */}
      <Bloco ancora="fap" titulo="FAP publicado" acao={<BotaoEditar bloco="fap" />}>
        <FapBloco estab={estab} embutido editando={editando === "fap"}
          onFechar={() => setEditando(null)} />
      </Bloco>

      <Bloco ancora="rat" titulo="RAT aplicado pela empresa" acao={<BotaoEditar bloco="rat" />}>
        {editando === "rat" ? (
          <RatAplicadoModal estab={estab} onFechar={() => setEditando(null)} embutido />
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 p-5">
            {(ratApl || []).length === 0 ? (
              <p className="text-xs text-gray-500">Nada declarado — é o número que a empresa usou na folha.</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wide text-gray-500 text-left">
                    <th className="py-1">Período</th><th>RAT</th><th>FAP</th><th>Efetiva</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(ratApl || []).map((x: any, i: number) => (
                    <tr key={i} className="text-gray-700">
                      <td className="py-2">{fmt.competencia(x.inicio)} {x.fim ? `a ${fmt.competencia(x.fim)}` : "em diante"}</td>
                      <td>{x.aliquota_rat == null ? "—" : fmt.pct(x.aliquota_rat)}</td>
                      <td>{x.fap_aplicado == null ? "—" : fmt.num(x.fap_aplicado, 4)}</td>
                      <td>{x.aliquota == null ? "—" : fmt.pct(x.aliquota)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </Bloco>

      {/* ITEM 7: O RESULTADO APARECE POR ANO, NAO POR MES. Seis linhas em vez de sessenta, e a
          inversao de crédito para débito fica visível de relance. A série mensal, a conferência
          e a memória continuam a um clique — a janela antiga vira um painel que abre sob demanda,
          e não o conteúdo padrão do bloco.

          Os números vêm do resumo do servidor (etapa A), as mesmas funções que a memória de
          cálculo usa: a tela não soma nada por conta própria. */}
      <Bloco ancora="enquadramento" titulo="Enquadramento — resumo por ano">
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <div className="flex justify-end mb-2">
            <button onClick={() => setSerieAberta((v) => !v)}
              className="text-xs text-indigo-700 hover:underline">
              {serieAberta ? "fechar a série mensal" : "abrir série mensal e conferência"}
            </button>
          </div>
          {(r.resumo_ano || []).length === 0 ? (
            <p className="text-xs text-gray-500">Nenhuma competência apurada nesta janela.</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] uppercase tracking-wide text-gray-500 text-left">
                  <th className="py-1">Ano</th><th>Comp.</th><th>Preponderante</th>
                  <th>Devida</th><th>Aplicada</th><th>Divergência</th><th>Situação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(r.resumo_ano || []).map((l: any) => {
                  // "varia" quando as competências do ano não concordam: resumir doze valores
                  // numa célula só é honesto enquanto eles forem o mesmo valor.
                  const cel = (v: any, varia: boolean, fmtv: (x: any) => string) =>
                    varia ? <span className="text-gray-400">varia</span> : (v == null ? "—" : fmtv(v));
                  const d = l.divergencia_pp;
                  return (
                    <tr key={l.ano} className="text-gray-700">
                      <td className="py-2 font-medium">{l.ano}</td>
                      <td>{l.competencias}</td>
                      <td className="font-mono">{cel(l.cnae_preponderante, l.cnae_preponderante_varia, (x) => fmt.cnae(x))}</td>
                      {/* A DEVIDA E A EFETIVA: RAT do grau × FAP publicado do ano. Mostrar o RAT
                          puro aqui punha 3,00% em todos os anos ao lado de uma divergência
                          calculada sobre outro número, e a conta não fechava na tela. Sem FAP
                          publicado não há efetiva, e a célula diz "—" em vez de inventar uma. */}
                      <td>{cel(l.aliquota_efetiva, l.aliquota_efetiva_varia, (x) => fmt.pct(x))}</td>
                      <td>{cel(l.aliquota_aplicada, l.aliquota_aplicada_varia, (x) => fmt.pct(x))}</td>
                      <td>
                        {l.divergencia_pp_varia ? <span className="text-gray-400">varia</span>
                          : d == null ? <span className="text-gray-400">não apurada</span>
                          : d === 0 ? "0,00 p.p."
                          : <b className={d > 0 ? "text-indigo-700" : "text-red-700"}>
                              {fmt.pp(d)} {d > 0 ? "crédito" : "débito"}
                            </b>}
                      </td>
                      <td>{l.situacao === "conferencia" ? "em conferência"
                          : l.situacao === "nao_auditada" ? "não auditada"
                          : l.situacao === "conferido" ? "conferida" : "apurada"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
        {/* ITEM 10: AS VIGENCIAS QUE A SERIE ATRAVESSA. Ela: "a fundamentação da série diz
            'vigente em 11/2021, início da série', mas a série atravessa a IN 971/2009 (até
            09/2022) e a IN 2.110/2022 (de 10/2022 em diante). Tem que mostrar as duas vigências,
            como a memória de cálculo já faz."

            Os blocos vêm resolvidos do servidor, pela mesma função que a memória usa: cada
            competência no seu fechamento, e meses consecutivos com a mesma redação colapsados
            num bloco. A tela não decide nada sobre vigência. */}
        {(r.fundamentacao_blocos || []).length > 0 && (
          <div className="mt-3 text-[11px] text-gray-500 space-y-1">
            {(r.fundamentacao_blocos || []).map((b: any, i: number) => (
              <div key={i} className={i > 0 ? "mt-2 pt-2 border-t border-gray-100" : ""}>
                <p className="text-gray-400">
                  {fmt.competencia(b.de)} a {fmt.competencia(b.ate)}
                </p>
                {/* OS TRES CAMPOS, em linhas separadas, como a memória de cálculo já imprime.
                    A tela mostrava só `dispositivo` — a Lei e o Decreto — e por isso as duas
                    vigências saíam idênticas: o que as distingue é a IN, que vive em
                    `ato_normativo`, e o anexo, que vive em `anexo`. O dado sempre esteve certo;
                    faltava exibi-lo.

                    E saiu a nota genérica "redação vigente desde …": colada ao fim de uma citação
                    que começa pelo Decreto, ela afirmava que o Decreto mudou em 17/10/2022, o que
                    é falso. A data agora acompanha a IN, dentro do próprio campo. */}
                {b.dispositivo
                  ? <p className="text-gray-600">{b.dispositivo}</p>
                  : <p className="text-amber-700">sem fundamentação cadastrada</p>}
                {b.ato && <p className="text-gray-600">{b.ato}</p>}
                {/* O MESMO rótulo da memória de cálculo ("Grau de risco: …"), para a tela e o
                    documento dizerem a mesma coisa com as mesmas palavras. O campo chegava vazio
                    até 28/10 porque o endpoint da página não o serializava. */}
                {b.anexo && <p className="text-gray-500">Grau de risco: {b.anexo}</p>}
              </div>
            ))}
          </div>
        )}

        {serieAberta && (
          <div className="mt-3">
            <PainelModal estab={estab} onFechar={() => setSerieAberta(false)} embutido />
          </div>
        )}
      </Bloco>

      <Bloco ancora="fpas" titulo="FPAS e Terceiros" acao={<BotaoEditar bloco="fpas" />}>
        {editando === "fpas" ? (
          <FpasModal estab={estab} onFechar={() => setEditando(null)} embutido />
        ) : (
          <Leitura>Clique em “editar” para ver e alterar os períodos de FPAS e Terceiros.</Leitura>
        )}
      </Bloco>
    </div>
  );
}
