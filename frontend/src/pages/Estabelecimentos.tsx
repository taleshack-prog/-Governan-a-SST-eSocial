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
        <h2 className="text-lg font-bold text-gray-900">Atividades — {estab.nome}</h2>
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
          <h2 className="text-lg font-bold text-gray-900">Enquadramento apurado — {estab.nome}</h2>
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
        {rows.length > 0 && rows[0].competencia && (
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
        <h2 className="text-lg font-bold text-gray-900">RAT aplicado pela empresa — {estab.nome}</h2>
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
        <h2 className="text-lg font-bold text-gray-900">FPAS — {estab.nome}</h2>
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

export function Estabelecimentos() {
  const qc = useQueryClient();
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState<any>(FORM_VAZIO);
  const [erro, setErro] = useState("");
  const [ativEstab, setAtivEstab] = useState<any>(null);
  const [painelEstab, setPainelEstab] = useState<any>(null);
  const [ratEstab, setRatEstab] = useState<any>(null);
  const [fpasPeriodoEstab, setFpasPeriodoEstab] = useState<any>(null);
  const navegar = useNavigate();
  const [fapEstab, setFapEstab] = useState<any>(null);
  const [fapValores, setFapValores] = useState<Record<number, string>>({});
  const [fapSalvando, setFapSalvando] = useState(false);
  const [busca, setBusca] = useState("");
  const [ordem, setOrdem] = useState("codigo");
  const ANOS_FAP = [2021, 2022, 2023, 2024, 2025, 2026];

  const { data: estabs = [], isLoading } = useQuery({
    queryKey: ["estabelecimentos"],
    queryFn: () => apiClient.get("/estabelecimentos/").then((r) => r.data),
  });

  // Item 10: busca e ordenação no cliente — a lista de um escritório não justifica paginar no
  // servidor, e "maior divergência primeiro" é a ordem que responde "onde eu olho".
  const visiveis = (() => {
    const q = busca.trim().toLowerCase();
    const filtrados = !q ? [...estabs] : estabs.filter((e: any) =>
      [e.codigo, e.nome, e.cnpj, e.identificador].some((v: any) => String(v || "").toLowerCase().includes(q)));
    const falta = (e: any) => e.completude
      ? Object.values(e.completude).filter((v) => !v).length : 9;
    const div = (e: any) => Math.abs(e.enquadramento_atual?.divergencia_pp ?? -1);
    filtrados.sort((a: any, b: any) =>
      ordem === "nome" ? String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR")
      : ordem === "divergencia" ? div(b) - div(a)
      : ordem === "incompleto" ? falta(b) - falta(a)
      : String(a.codigo || "").localeCompare(String(b.codigo || ""), "pt-BR", { numeric: true }));
    return filtrados;
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

  const abrirFap = async (e: any) => {
    setFapEstab(e);
    try { const r = await apiClient.get(`/estabelecimentos/${e.id}/fap`); const m: Record<number, string> = {}; (r.data || []).forEach((x: any) => { m[x.ano] = fmt.num(x.fap, 4); }); setFapValores(m); }
    catch { setFapValores({}); }
  };
  const salvarFap = async () => {
    if (!fapEstab) return; setFapSalvando(true);
    try {
      const faps = ANOS_FAP.filter((a) => fapValores[a] !== undefined && fapValores[a] !== "").map((a) => ({ ano: a, fap: Number(String(fapValores[a]).replace(".", "").replace(",", ".")) }));
      await apiClient.put(`/estabelecimentos/${fapEstab.id}/fap`, faps); setFapEstab(null);
    } catch { alert("Não foi possível salvar o FAP."); } finally { setFapSalvando(false); }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Estabelecimentos</h1>
          <p className="text-sm text-gray-500 mt-1">Matriz, filiais e obras. O grau de risco é apurado da atividade preponderante.</p>
        </div>
        <button onClick={() => { setForm(FORM_VAZIO); setErro(""); setModal(true); }}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Novo</button>
      </div>

      {/* Item 10: busca e ordenação. Com quinze linhas, achar um estabelecimento rolando a lista
          já não funciona; com quarenta obras, menos ainda. */}
      <div className="flex flex-wrap items-center gap-3">
        <input className="flex-1 min-w-[220px] border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={busca} onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por código, nome, CNPJ ou matrícula…" />
        <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={ordem}
          onChange={(e) => setOrdem(e.target.value)}>
          <option value="codigo">Ordenar por código</option>
          <option value="nome">Ordenar por nome</option>
          <option value="divergencia">Maior divergência primeiro</option>
          <option value="incompleto">Menos completo primeiro</option>
        </select>
        <span className="text-xs text-gray-400">{visiveis.length} de {estabs.length}</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {isLoading ? <div className="p-8 text-center text-gray-400">Carregando…</div>
          : estabs.length === 0 ? <div className="p-8 text-center text-gray-400">Nenhum estabelecimento.</div>
          : visiveis.length === 0 ? <div className="p-8 text-center text-gray-400">Nenhum estabelecimento corresponde à busca.</div>
          : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>{["Código", "Nome", "CNPJ / matrícula", "Natureza", "Grau", "RAT devido",
                      "Efetiva", "Divergência", "Situação", "Abertura", "Completude", "Ações"].map((h) => (
                  <th key={h} className="text-left px-3 py-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{h}</th>))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {visiveis.map((e: any) => {
                  const a = e.enquadramento_atual;
                  const comp = a?.competencia ? `competência ${fmt.competencia(a.competencia)}` : "série não apurada";
                  // A LINHA ABRE A PÁGINA (etapa B). As ações continuam onde estavam até a
                  // etapa C reescrever a lista; clicar fora delas leva ao estabelecimento.
                  return (
                  <tr key={e.id} className="hover:bg-gray-50 cursor-pointer"
                    onClick={(ev) => {
                      // Só navega quando o clique não foi num botão ou link da própria linha:
                      // senão "Atividades" abriria a janela e a página ao mesmo tempo.
                      if ((ev.target as HTMLElement).closest("button,a,input,select")) return;
                      navegar(`/estabelecimentos/${e.id}`);
                    }}>
                    <td className="px-3 py-3 font-mono text-gray-600 text-xs">{e.codigo}</td>
                    <td className="px-3 py-3 font-medium text-gray-900">
                      {e.nome}
                      <span className="block text-[11px] text-gray-400 capitalize">{e.posicao} · {e.status}</span>
                    </td>
                    <td className="px-3 py-3 font-mono text-gray-600 text-xs">{e.cnpj ? maskCnpj(e.cnpj) : (e.identificador || "—")}</td>
                    <td className="px-3 py-3 text-gray-600">{e.tipo_estabelecimento}</td>
                    {/* Enquadramento apurado da competência corrente — somente leitura */}
                    <td className="px-3 py-3 text-gray-600 whitespace-nowrap" title={comp}>
                      {a?.grau_risco ? <span>{a.grau_risco} <span className="text-gray-400 text-xs">{a.grau_label}</span></span> : "—"}
                    </td>
                    <td className="px-3 py-3 text-gray-600 tabular-nums" title={comp}>{fmt.pct(a?.aliquota_devida)}</td>
                    <td className="px-3 py-3 text-gray-600 tabular-nums" title={comp}>{fmt.pct(a?.aliquota_efetiva)}</td>
                    {/* Item 9: a divergência é o que diz QUAL estabelecimento tem problema.
                        Positiva = crédito; negativa = passivo. Cor acompanhada de rótulo. */}
                    <td className="px-3 py-3 tabular-nums whitespace-nowrap">
                      {a?.divergencia_confirmada === false ? (
                        <span className="text-amber-700" title="Divergência não confirmada: depende de informar o RAT base e o FAP aplicados.">
                          <b>?</b>
                          <span className="block text-[11px] font-normal">não confirmada</span>
                        </span>
                      ) : a?.divergencia_pp == null ? <span className="text-gray-400">—</span> : (
                        <span className={a.divergencia_pp > 0 ? "text-blue-700" : a.divergencia_pp < 0 ? "text-red-700" : "text-gray-500"}
                          title={a.divergencia_pp > 0 ? "pagou a mais — crédito a recuperar" : a.divergencia_pp < 0 ? "pagou a menos — passivo a regularizar" : "sem divergência"}>
                          <b>{fmt.pp(a.divergencia_pp)}</b>
                          {a.origem_divergencia && a.origem_divergencia !== "nenhuma" && (
                            <span className="block text-[11px] font-normal">
                              {ORIGEM[a.origem_divergencia] || a.origem_divergencia}
                              {a.amparada && <span className="text-gray-400" title="processo informado amparando a alíquota"> · amparada</span>}
                            </span>
                          )}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span className={SIT[a?.situacao]?.cls || "text-gray-400"} title={a?.motivo_fila || SIT[a?.situacao]?.ajuda || "série não apurada"}>
                        {SIT[a?.situacao]?.txt || "—"}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-gray-600 whitespace-nowrap">{fmt.data(e.data_abertura)}</td>
                    {/* Item 10: o que falta, sem abrir cada estabelecimento */}
                    <td className="px-3 py-3 whitespace-nowrap">
                      {e.completude ? (
                        <span className="flex gap-1">
                          {([["atividade", "At"], ["fap", "FAP"], ["rat_aplicado", "RAT"], ["fpas", "FPAS"]] as const).map(([k, lbl]) => (
                            <span key={k}
                              title={`${lbl === "At" ? "Atividade" : lbl}: ${e.completude[k] ? "informado" : "faltando"}`}
                              className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                e.completude[k] ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-400"}`}>
                              {lbl}
                            </span>
                          ))}
                        </span>
                      ) : "—"}
                    </td>
                    {/* Item 10: cor só onde significa algo. Enquadramento é o resultado (verde);
                        os insumos ficam neutros; Editar é secundário. */}
                    <td className="px-3 py-3 text-xs whitespace-nowrap">
                      <button onClick={() => setPainelEstab(e)} className="text-emerald-700 font-medium hover:underline">Enquadramento</button>
                      <span className="text-gray-300 mx-2">|</span>
                      <span className="space-x-2 text-gray-600">
                        <button onClick={() => setAtivEstab(e)} className="hover:underline hover:text-gray-900">Atividades</button>
                        <button onClick={() => abrirFap(e)} className="hover:underline hover:text-gray-900">FAP</button>
                        <button onClick={() => setRatEstab(e)} className="hover:underline hover:text-gray-900">RAT aplicado</button>
                        <button onClick={() => setFpasPeriodoEstab(e)} className="hover:underline hover:text-gray-900">FPAS</button>
                      </span>
                      <span className="text-gray-300 mx-2">|</span>
                      <button onClick={() => { setForm({ ...FORM_VAZIO, ...e, data_abertura: e.data_abertura || "", data_encerramento: e.data_encerramento || "" }); setErro(""); setModal(true); }} className="text-gray-400 hover:underline hover:text-gray-700">Editar</button>
                    </td>
                  </tr>
                );})}
              </tbody>
            </table>
          )}
      </div>

      {modal && <EstabModal form={form} setForm={setForm} onSalvar={onSalvar} onFechar={() => { setModal(false); setForm(FORM_VAZIO); }} isPending={salvar.isPending} erro={erro} />}
      {ativEstab && <AtividadesModal estab={ativEstab} onFechar={() => setAtivEstab(null)} />}
      {painelEstab && <PainelModal estab={painelEstab} onFechar={() => setPainelEstab(null)} />}
      {/* Reapura a série ao fechar: grau/RAT da listagem precisam refletir o que acabou de mudar */}
      {ratEstab && <RatAplicadoModal estab={ratEstab} onFechar={() => { setRatEstab(null); qc.invalidateQueries({ queryKey: ["estabelecimentos"] }); }} />}
      {fpasPeriodoEstab && <FpasModal estab={fpasPeriodoEstab} onFechar={() => setFpasPeriodoEstab(null)} />}
      {fapEstab && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold text-gray-900">FAP por ano — {fapEstab.nome}<Fundamentacao campo="fap_publicado" em={hojeISO()} /></h2>
            <p className="text-xs text-gray-500 mt-1 mb-4">O cálculo usa o FAP de cada ano. Campo vazio não é 1,0 — fica em branco e vai à conferência.</p>
            <div className="space-y-2">
              {ANOS_FAP.map((ano) => (
                <div key={ano} className="flex items-center gap-3">
                  <label className="w-16 text-sm text-gray-600">{ano}</label>
                  <input type="text" inputMode="decimal" className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm tabular-nums"
                    value={fapValores[ano] ?? ""}
                    onChange={(ev) => setFapValores((v) => ({ ...v, [ano]: ev.target.value }))}
                    onBlur={(ev) => {
                      // Quatro casas, com vírgula: é assim que a norma define o FAP.
                      const n = Number(String(ev.target.value).replace(",", "."));
                      setFapValores((v) => ({ ...v, [ano]: ev.target.value === "" || Number.isNaN(n) ? "" : fmt.num(n, 4) }));
                    }}
                    placeholder="não informado" />
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setFapEstab(null)} className="px-4 py-2 text-sm text-gray-600">Cancelar</button>
              <button onClick={salvarFap} disabled={fapSalvando} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">{fapSalvando ? "Salvando…" : "Salvar FAP"}</button>
            </div>
          </div>
        </div>
      )}
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

  const Bloco = ({ ancora, titulo, children }: { ancora: string; titulo: string; children: any }) => (
    <section id={`bloco-${ancora}`} className="scroll-mt-24 mb-4">
      <h2 className="text-sm font-bold text-gray-800 mb-2">{titulo}</h2>
      {children}
    </section>
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
        <span className="font-mono">{estab.cnpj || estab.cno || "—"}</span>
        {estab.municipio ? ` · ${estab.municipio}/${estab.uf || ""}` : ""}
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
          <div><p className="text-[11px] text-gray-500">Natureza</p><p>{estab.natureza || "—"}</p></div>
          <div><p className="text-[11px] text-gray-500">CNPJ / CNO</p><p className="font-mono">{estab.cnpj || estab.cno || "—"}</p></div>
          <div><p className="text-[11px] text-gray-500">Abertura</p><p>{estab.data_abertura ? fmt.data(estab.data_abertura) : "—"}</p></div>
          <div><p className="text-[11px] text-gray-500">Situação</p><p>{estab.status || "—"}</p></div>
        </div>
      </Bloco>

      {/* Os quatro blocos abaixo são as antigas janelas, agora embutidas. O conteúdo e a gravação
          são os mesmos; some só a moldura flutuante. */}
      <Bloco ancora="atividades" titulo="Atividades — quantitativo de segurados empregados e avulsos">
        <AtividadesModal estab={estab} onFechar={() => {}} embutido />
      </Bloco>

      {/* O FAP ainda não é um componente próprio: hoje ele vive dentro do componente da lista,
          usando o estado dela (fapValores, fapSalvando). Extraí-lo é a primeira coisa da etapa C,
          quando a lista for reescrita. Declarar a ausência aqui é melhor do que uma página que
          simplesmente não mostra o FAP e deixa quem lê procurando. */}
      <Bloco ancora="fap" titulo="FAP publicado">
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <p className="text-xs text-gray-500">
            Bloco ainda na lista — entra aqui na etapa C, junto com a reescrita dela.
          </p>
        </div>
      </Bloco>

      <Bloco ancora="rat" titulo="RAT aplicado pela empresa">
        <RatAplicadoModal estab={estab} onFechar={() => {}} embutido />
      </Bloco>

      <Bloco ancora="enquadramento" titulo="Enquadramento">
        <PainelModal estab={estab} onFechar={() => {}} embutido />
      </Bloco>

      <Bloco ancora="fpas" titulo="FPAS e Terceiros">
        <FpasModal estab={estab} onFechar={() => {}} embutido />
      </Bloco>
    </div>
  );
}
