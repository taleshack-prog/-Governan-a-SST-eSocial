// ==============================================================
// SST ESOCIAL GOV — Estabelecimentos (Adendo 04, v1 / Fase 2)
// O grau de risco é DERIVADO da atividade preponderante (RN-20). Aqui a empresa declara os
// insumos: natureza/datas e a lista de atividades com quantitativo por período.
// ==============================================================
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";

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

const FORM_VAZIO = {
  id: "", codigo: "", nome: "", tipo_estabelecimento: "CNPJ", posicao: "filial",
  cnpj: "", identificador: "", status: "ativa", endereco: "", cidade: "", uf: "",
  data_abertura: "", data_encerramento: "",
};
const inp = "w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-sm";
const lbl = "text-xs font-medium text-gray-600";

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
function AtividadesModal({ estab, onFechar }: { estab: any; onFechar: () => void }) {
  const [rows, setRows] = useState<any[]>([]);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  useEffect(() => {
    apiClient.get(`/estabelecimentos/${estab.id}/atividades`).then((r) => setRows(r.data || [])).catch(() => setRows([]));
  }, [estab.id]);
  const upd = (i: number, k: string, v: any) => setRows((l) => l.map((x, j) => j === i ? { ...x, [k]: v } : x));
  const salvar = async () => {
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-6 w-full max-w-3xl shadow-xl max-h-[90vh] overflow-y-auto">
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
function PainelModal({ estab, onFechar }: { estab: any; onFechar: () => void }) {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [apurando, setApurando] = useState(false);
  const load = () => { setLoading(true); apiClient.get(`/estabelecimentos/${estab.id}/enquadramento`).then((r) => setRows(r.data || [])).catch(() => setRows([])).finally(() => setLoading(false)); };
  useEffect(load, [estab.id]);
  const apurar = async () => { setApurando(true); try { await apiClient.post(`/estabelecimentos/${estab.id}/apurar`); load(); } catch { /* */ } finally { setApurando(false); } };
  const emFila = rows.filter((r) => r.em_fila).length;
  const fund = rows.find((r) => r.fundamentacao)?.fundamentacao;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-6 w-full max-w-5xl shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Enquadramento apurado — {estab.nome}</h2>
          <div className="flex gap-2">
            <button onClick={async () => {
              try {
                const r = await apiClient.get(`/estabelecimentos/${estab.id}/memoria`, { responseType: "blob" });
                const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
                window.open(url, "_blank");
              } catch { alert("Não foi possível gerar a memória."); }
            }} className="text-xs border border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50">Memória (PDF)</button>
            <button onClick={apurar} disabled={apurando} className="text-xs bg-teal-600 text-white px-3 py-1.5 rounded-lg hover:bg-teal-700 disabled:opacity-50">{apurando ? "Apurando…" : "Reapurar"}</button>
          </div>
        </div>
        <p className="text-[11px] text-gray-400 mt-1 mb-3">
          Série mensal. Grau e RAT devido derivados da atividade preponderante (Anexo I). {emFila > 0 && <span className="text-amber-600">{emFila} competência(s) em conferência.</span>}
        </p>
        {loading ? <div className="p-6 text-center text-gray-400 text-sm">Carregando…</div>
          : rows.length === 0 ? <div className="p-6 text-center text-gray-400 text-sm">Nada apurado. Cadastre atividades (com quantitativo) e FAP; a série aparece aqui.</div>
          : (
            <table className="w-full text-xs">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-500">
                <tr>{["Comp.", "Preponderante", "Critério", "Grau", "Devido", "FAP", "Efetivo", "Aplicado", "Diverg.", "Situação"].map((h) => <th key={h} className="text-left px-2 py-2 font-medium">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((r, i) => (
                  <tr key={i} className={r.em_fila ? "bg-amber-50" : "hover:bg-gray-50"}>
                    <td className="px-2 py-1.5 font-mono">{r.competencia?.slice(0, 7)}</td>
                    <td className="px-2 py-1.5">{r.cnae_preponderante || "—"}</td>
                    <td className="px-2 py-1.5 text-gray-500">{CRIT[r.criterio] || r.criterio || "—"}</td>
                    <td className="px-2 py-1.5">{r.grau_risco ?? "—"}</td>
                    <td className="px-2 py-1.5">{r.aliquota_devida != null ? `${r.aliquota_devida.toFixed(2)}%` : "—"}</td>
                    <td className="px-2 py-1.5">{r.fap != null ? r.fap.toFixed(4) : "—"}</td>
                    <td className="px-2 py-1.5">{r.aliquota_efetiva != null ? `${r.aliquota_efetiva.toFixed(4)}%` : "—"}</td>
                    <td className="px-2 py-1.5">{r.aliquota_aplicada != null ? `${r.aliquota_aplicada.toFixed(2)}%` : "—"}</td>
                    <td className={`px-2 py-1.5 font-medium ${r.divergencia_pp ? "text-amber-700" : "text-gray-400"}`}>{r.divergencia_pp != null ? `${r.divergencia_pp > 0 ? "+" : ""}${r.divergencia_pp.toFixed(2)} p.p.` : "—"}</td>
                    <td className="px-2 py-1.5">{r.em_fila ? <span className="text-amber-700" title={r.motivo_fila}>⚠ conferência</span> : <span className="text-emerald-600">ok</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        {fund && <p className="text-[11px] text-gray-400 mt-3">Fundamentação: {fund.dispositivo}; {fund.ato_normativo}; {fund.anexo}.</p>}
        <div className="flex justify-end mt-4"><button onClick={onFechar} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Fechar</button></div>
      </div>
    </div>
  );
}

// ---------- Modal de estabelecimento ----------
function EstabModal({ form, setForm, onSalvar, onFechar, isPending, erro }: any) {
  const editando = !!form.id;
  const cnpjInvalido = form.tipo_estabelecimento === "CNPJ" && form.cnpj && !validaCnpj(form.cnpj);
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
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
            <div><label className={lbl}>{form.tipo_estabelecimento === "CNO" ? "Matrícula CNO *" : "Identificador (CAEPF)"}</label>
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
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-3"><label className={lbl}>Endereço</label><input className={inp} value={form.endereco} onChange={(e) => setForm({ ...form, endereco: e.target.value })} /></div>
            <div className="col-span-2"><label className={lbl}>Cidade</label><input className={inp} value={form.cidade} onChange={(e) => setForm({ ...form, cidade: e.target.value })} /></div>
            <div><label className={lbl}>UF</label><input className={inp} value={form.uf} maxLength={2} onChange={(e) => setForm({ ...form, uf: e.target.value.toUpperCase() })} /></div>
          </div>
          <p className="text-[11px] text-gray-400">O grau de risco e o RAT devido são derivados da atividade preponderante (não se escolhem aqui). Cadastre as atividades após salvar.</p>
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
  const [fapEstab, setFapEstab] = useState<any>(null);
  const [fapValores, setFapValores] = useState<Record<number, string>>({});
  const [fapSalvando, setFapSalvando] = useState(false);
  const ANOS_FAP = [2021, 2022, 2023, 2024, 2025, 2026];

  const { data: estabs = [], isLoading } = useQuery({
    queryKey: ["estabelecimentos"],
    queryFn: () => apiClient.get("/estabelecimentos/").then((r) => r.data),
  });

  const salvar = useMutation({
    mutationFn: (d: any) => d.id ? apiClient.put(`/estabelecimentos/${d.id}`, d) : apiClient.post("/estabelecimentos/", d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["estabelecimentos"] }); setModal(false); setForm(FORM_VAZIO); },
    onError: (e: any) => setErro(e?.response?.data?.detail || "Tente novamente."),
  });

  const onSalvar = () => {
    setErro("");
    const p: any = { ...form };
    ["cnpj", "identificador", "endereco", "cidade", "uf", "data_encerramento"].forEach((k) => { if (!p[k]) p[k] = null; });
    if (!p.id) delete p.id;
    salvar.mutate(p);
  };

  const abrirFap = async (e: any) => {
    setFapEstab(e);
    try { const r = await apiClient.get(`/estabelecimentos/${e.id}/fap`); const m: Record<number, string> = {}; (r.data || []).forEach((x: any) => { m[x.ano] = String(x.fap); }); setFapValores(m); }
    catch { setFapValores({}); }
  };
  const salvarFap = async () => {
    if (!fapEstab) return; setFapSalvando(true);
    try {
      const faps = ANOS_FAP.filter((a) => fapValores[a] !== undefined && fapValores[a] !== "").map((a) => ({ ano: a, fap: Number(fapValores[a]) }));
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

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? <div className="p-8 text-center text-gray-400">Carregando…</div>
          : estabs.length === 0 ? <div className="p-8 text-center text-gray-400">Nenhum estabelecimento.</div>
          : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>{["Código", "Nome", "Natureza", "Posição", "Abertura", "Status", "Ações"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">{h}</th>))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {estabs.map((e: any) => (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-600 text-xs">{e.codigo}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{e.nome}</td>
                    <td className="px-4 py-3 text-gray-600">{e.tipo_estabelecimento}</td>
                    <td className="px-4 py-3 text-gray-600 capitalize">{e.posicao}</td>
                    <td className="px-4 py-3 text-gray-600">{e.data_abertura || "—"}</td>
                    <td className="px-4 py-3 text-gray-600 capitalize">{e.status}</td>
                    <td className="px-4 py-3 space-x-3 text-xs">
                      <button onClick={() => setAtivEstab(e)} className="text-teal-700 hover:underline">Atividades</button>
                      <button onClick={() => setPainelEstab(e)} className="text-emerald-700 hover:underline">Enquadramento</button>
                      <button onClick={() => abrirFap(e)} className="text-indigo-600 hover:underline">FAP/ano</button>
                      <button onClick={() => { setForm({ ...FORM_VAZIO, ...e, data_abertura: e.data_abertura || "", data_encerramento: e.data_encerramento || "" }); setErro(""); setModal(true); }} className="text-gray-500 hover:underline">Editar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>

      {modal && <EstabModal form={form} setForm={setForm} onSalvar={onSalvar} onFechar={() => { setModal(false); setForm(FORM_VAZIO); }} isPending={salvar.isPending} erro={erro} />}
      {ativEstab && <AtividadesModal estab={ativEstab} onFechar={() => setAtivEstab(null)} />}
      {painelEstab && <PainelModal estab={painelEstab} onFechar={() => setPainelEstab(null)} />}
      {fapEstab && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold text-gray-900">FAP por ano — {fapEstab.nome}</h2>
            <p className="text-xs text-gray-500 mt-1 mb-4">O cálculo usa o FAP de cada ano. Campo vazio não é 1,0 — fica em branco e vai à conferência.</p>
            <div className="space-y-2">
              {ANOS_FAP.map((ano) => (
                <div key={ano} className="flex items-center gap-3">
                  <label className="w-16 text-sm text-gray-600">{ano}</label>
                  <input type="number" step="0.0001" min="0.5" max="2.0" className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    value={fapValores[ano] ?? ""} onChange={(ev) => setFapValores((v) => ({ ...v, [ano]: ev.target.value }))} placeholder="1,0000" />
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
