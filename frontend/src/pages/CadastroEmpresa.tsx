// ==============================================================
// SST ESOCIAL GOV — Cadastro da Empresa (Adendo 03, v1)
// O enquadramento é do ESTABELECIMENTO (matriz), não da empresa (RN-17). Esta tela guarda
// identificação, período de apuração, regime/CPRB por período e contato; o enquadramento
// aparece como espelho read-only da matriz.
// ==============================================================
import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";

const REGIMES = [
  { v: "lucro_real", label: "Lucro Real" },
  { v: "lucro_presumido", label: "Lucro Presumido" },
  { v: "simples", label: "Simples Nacional" },
];
const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];

const maskCnpj = (v: string) => (v || "").replace(/\D/g, "").slice(0, 14)
  .replace(/^(\d{2})(\d)/, "$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
  .replace(/\.(\d{3})(\d)/, ".$1/$2").replace(/(\d{4})(\d)/, "$1-$2");
const maskCep = (v: string) => (v || "").replace(/\D/g, "").slice(0, 8).replace(/^(\d{5})(\d)/, "$1-$2");
const validaCnpj = (v: string): boolean => {
  const c = (v || "").replace(/\D/g, "");
  if (c.length !== 14 || /^(\d)\1{13}$/.test(c)) return false;
  const dv = (base: string) => {
    let soma = 0, pos = base.length - 7;
    for (let i = 0; i < base.length; i++) { soma += parseInt(base[i], 10) * pos--; if (pos < 2) pos = 9; }
    const r = soma % 11; return r < 2 ? 0 : 11 - r;
  };
  return dv(c.slice(0, 12)) === +c[12] && dv(c.slice(0, 13)) === +c[13];
};

// competências (AAAA-MM)
const ym = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const ymToday = () => ym(new Date());
const ymMinus = (months: number) => { const d = new Date(); d.setMonth(d.getMonth() - months); return ym(d); };
const ymToDate = (s: string) => (s ? `${s}-01` : null);
const dateToYm = (iso: string | null) => (iso ? iso.slice(0, 7) : "");
const mesesEntre = (a: string, b: string) => {
  if (!a || !b) return 0;
  const [ya, ma] = a.split("-").map(Number), [yb, mb] = b.split("-").map(Number);
  return (yb - ya) * 12 + (mb - ma);
};

interface Periodo { regime?: string; anexo_simples?: string; inicio: string; fim: string; }

export function CadastroEmpresa() {
  const empresaId = useAuthStore((s) => s.user?.empresa_id);
  const [form, setForm] = useState<any>({
    razao_social: "", nome_fantasia: "", cnpj: "", cnae_principal: "",
    periodo_inicio: ymMinus(59), periodo_fim: ymToday(),
    endereco: "", numero: "", complemento: "", bairro: "", cidade: "", uf: "", cep: "",
    contato_nome: "", contato_email: "", contato_telefone: "",
  });
  const [origem, setOrigem] = useState<string>("");          // consultado | declarado
  const [secundarios, setSecundarios] = useState<any[]>([]);
  const [regimes, setRegimes] = useState<Periodo[]>([]);
  const [cprb, setCprb] = useState<Periodo[]>([]);
  const [espelho, setEspelho] = useState<any>(null);
  const [numEstab, setNumEstab] = useState<number>(0);
  const [cnpjErro, setCnpjErro] = useState("");
  const [consultaMsg, setConsultaMsg] = useState("");
  const [cepMsg, setCepMsg] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState("");

  const set = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  // carrega empresa + regime + cprb + espelho
  useEffect(() => {
    if (!empresaId) return;
    apiClient.get(`/empresas/${empresaId}`).then((r) => {
      const d = r.data;
      setForm((f: any) => ({
        ...f,
        razao_social: d.razao_social ?? "", nome_fantasia: d.nome_fantasia ?? "",
        cnpj: d.cnpj ?? "", cnae_principal: d.cnae_principal ?? "",
        periodo_inicio: dateToYm(d.periodo_apuracao_inicio) || f.periodo_inicio,
        periodo_fim: dateToYm(d.periodo_apuracao_fim) || f.periodo_fim,
        endereco: d.endereco ?? "", numero: d.numero ?? "", complemento: d.complemento ?? "",
        bairro: d.bairro ?? "", cidade: d.cidade ?? "", uf: d.uf ?? "", cep: d.cep ?? "",
        contato_nome: d.contato_nome ?? "", contato_email: d.contato_email ?? "", contato_telefone: d.contato_telefone ?? "",
      }));
      setOrigem(d.origem_cadastro ?? "");
      setNumEstab(d.num_estabelecimentos ?? 0);
    }).catch(() => {});
    apiClient.get(`/empresas/${empresaId}/regime`).then((r) => setRegimes(r.data || [])).catch(() => {});
    apiClient.get(`/empresas/${empresaId}/cprb`).then((r) => setCprb(r.data || [])).catch(() => {});
    carregarEspelho();
  }, [empresaId]);

  const carregarEspelho = () => {
    if (!empresaId) return;
    apiClient.get(`/empresas/${empresaId}/matriz-enquadramento`).then((r) => setEspelho(r.data)).catch(() => {});
  };

  // Consulta de CNPJ pelo backend (RF-0.150)
  const consultarCnpj = async () => {
    const d = (form.cnpj || "").replace(/\D/g, "");
    if (!validaCnpj(d)) { setCnpjErro("CNPJ inválido (dígito verificador)."); return; }
    setCnpjErro(""); setConsultaMsg("Consultando dados públicos…");
    try {
      const r = await apiClient.get(`/empresas/consulta-cnpj/${d}`);
      const x = r.data;
      setForm((f: any) => ({
        ...f,
        razao_social: x.razao_social ?? f.razao_social,
        nome_fantasia: x.nome_fantasia ?? f.nome_fantasia,
        cnae_principal: x.cnae_principal ?? f.cnae_principal,
        endereco: x.logradouro ?? f.endereco, numero: x.numero ?? f.numero,
        complemento: x.complemento ?? f.complemento, bairro: x.bairro ?? f.bairro,
        cidade: x.municipio ?? f.cidade, uf: x.uf ?? f.uf, cep: x.cep ?? f.cep,
      }));
      setSecundarios(x.cnaes_secundarios || []);
      setOrigem("consultado");
      setConsultaMsg(`Consultado na Receita (${x.situacao_cadastral || "situação n/d"}). Revise e confirme — o dado vale após salvar.`);
    } catch (e: any) {
      setOrigem("declarado");
      setConsultaMsg(`${e?.response?.data?.detail || "Consulta indisponível"}. Preencha manualmente (origem: declarado).`);
    }
  };

  const buscarCep = async (cepRaw: string) => {
    const d = (cepRaw || "").replace(/\D/g, "");
    if (d.length !== 8) return;
    setCepMsg("Buscando endereço…");
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${d}/json/`);
      const data = await resp.json();
      if (data.erro) { setCepMsg("CEP não encontrado."); return; }
      setForm((f: any) => ({ ...f, endereco: data.logradouro || f.endereco, bairro: data.bairro || f.bairro, cidade: data.localidade || f.cidade, uf: data.uf || f.uf }));
      setCepMsg("");
    } catch { setCepMsg("Não foi possível buscar o CEP."); }
  };

  const salvar = async () => {
    if (!empresaId) return;
    if (form.cnpj && !validaCnpj(form.cnpj)) { setCnpjErro("CNPJ inválido (dígito verificador)."); setMsg("Corrija o CNPJ antes de salvar."); return; }
    if (mesesEntre(form.periodo_inicio, form.periodo_fim) < 0) { setMsg("Período de apuração: início depois do fim."); return; }
    setSalvando(true); setMsg("");
    try {
      await apiClient.put(`/empresas/${empresaId}`, {
        razao_social: form.razao_social, nome_fantasia: form.nome_fantasia, cnpj: form.cnpj,
        cnae_principal: form.cnae_principal || null,
        periodo_apuracao_inicio: ymToDate(form.periodo_inicio), periodo_apuracao_fim: ymToDate(form.periodo_fim),
        origem_cadastro: origem || "declarado",
        endereco: form.endereco, numero: form.numero, complemento: form.complemento,
        bairro: form.bairro, cidade: form.cidade, uf: form.uf, cep: form.cep,
        contato_nome: form.contato_nome, contato_email: form.contato_email, contato_telefone: form.contato_telefone,
      });
      await apiClient.put(`/empresas/${empresaId}/regime`, regimes.filter((p) => p.regime && p.inicio).map((p) => ({
        regime: p.regime, anexo_simples: p.regime === "simples" ? (p.anexo_simples || null) : null,
        inicio: ymToDate(p.inicio), fim: p.fim ? ymToDate(p.fim) : null,
      })));
      await apiClient.put(`/empresas/${empresaId}/cprb`, cprb.filter((p) => p.inicio).map((p) => ({
        inicio: ymToDate(p.inicio), fim: p.fim ? ymToDate(p.fim) : null,
      })));
      setMsg("Dados salvos. A matriz foi criada/atualizada e o enquadramento espelhado abaixo.");
      carregarEspelho();
      apiClient.get(`/empresas/${empresaId}`).then((r) => setNumEstab(r.data.num_estabelecimentos ?? numEstab)).catch(() => {});
    } catch {
      setMsg("Não foi possível salvar. Verifique os campos (períodos não podem se sobrepor).");
    } finally { setSalvando(false); }
  };

  const inputCls = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-500";
  const roCls = "w-full rounded-lg px-3 py-2 text-sm bg-teal-50 border border-teal-200 text-teal-900";
  const labelCls = "block text-xs font-medium text-gray-600 mb-1";
  const periodoLongo = mesesEntre(form.periodo_inicio, form.periodo_fim) > 60;

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900">Cadastro da Empresa</h1>
      <p className="text-sm text-gray-500 mt-1 mb-6">
        O enquadramento (CNAE, RAT, FPAS, FAP) pertence ao estabelecimento — aqui ele aparece como espelho da matriz.
      </p>

      {/* Identificação — CNPJ primeiro (RF-0.150) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Identificação</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>CNPJ raiz</label>
            <div className="flex gap-2">
              <input className={`${inputCls} ${cnpjErro ? "border-red-400" : ""}`} value={maskCnpj(form.cnpj)}
                onChange={(e) => { set("cnpj", e.target.value.replace(/\D/g, "").slice(0, 14)); if (cnpjErro) setCnpjErro(""); }}
                onBlur={(e) => { const d = e.target.value.replace(/\D/g, ""); setCnpjErro(d && !validaCnpj(d) ? "CNPJ inválido (dígito verificador)." : ""); }}
                maxLength={18} placeholder="00.000.000/0000-00" />
              <button type="button" onClick={consultarCnpj}
                className="shrink-0 px-3 py-2 rounded-lg text-sm bg-teal-600 text-white hover:bg-teal-700">Consultar</button>
            </div>
            {cnpjErro && <p className="text-[11px] text-red-500 mt-1">{cnpjErro}</p>}
            {consultaMsg && <p className="text-[11px] text-amber-600 mt-1">{consultaMsg}</p>}
            {origem && <p className="text-[11px] text-gray-400 mt-1">Origem do cadastro: <b>{origem}</b>{origem === "consultado" ? " (confirme antes de valer)" : ""}.</p>}
          </div>
          <div>
            <label className={labelCls}>Período de apuração (competências)</label>
            <div className="flex items-center gap-2">
              <input type="month" className={inputCls} value={form.periodo_inicio} onChange={(e) => set("periodo_inicio", e.target.value)} />
              <span className="text-gray-400">→</span>
              <input type="month" className={inputCls} value={form.periodo_fim} onChange={(e) => set("periodo_fim", e.target.value)} />
            </div>
            {periodoLongo && <p className="text-[11px] text-amber-600 mt-1">Intervalo acima de 5 anos — parte pode estar prescrita.</p>}
          </div>
          <div>
            <label className={labelCls}>Razão social</label>
            <input className={inputCls} value={form.razao_social} onChange={(e) => set("razao_social", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Nome fantasia</label>
            <input className={inputCls} value={form.nome_fantasia} onChange={(e) => set("nome_fantasia", e.target.value)} />
          </div>
        </div>
        {secundarios.length > 0 && (
          <p className="text-[11px] text-gray-400 mt-2">CNAEs secundários (consultados): {secundarios.map((c) => c.codigo).join(", ")}.</p>
        )}
      </section>

      {/* Espelho do enquadramento da matriz (RF-0.155) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-sm font-bold text-gray-800">Enquadramento da matriz</h2>
          <a href="/estabelecimentos" className="text-[11px] text-teal-700 hover:underline">editar em Estabelecimentos →</a>
        </div>
        <p className="text-[11px] text-gray-400 mb-3">🔒 pertence ao estabelecimento matriz — somente leitura aqui (RN-17).</p>
        {!espelho?.existe || !espelho?.enquadramento ? (
          <p className="text-xs text-gray-500">A matriz é criada ao salvar; o enquadramento aparece aqui depois.</p>
        ) : (
          <div className="grid grid-cols-4 gap-4">
            <div><label className={labelCls}>CNAE</label><div className={roCls}>{espelho.enquadramento.cnae || "—"}</div></div>
            <div><label className={labelCls}>Grau de risco</label><div className={roCls}>{espelho.enquadramento.grau_risco ? `${espelho.enquadramento.grau_risco} — ${espelho.enquadramento.grau_label}` : "—"}</div></div>
            <div><label className={labelCls}>RAT devido (%)</label><div className={roCls}>{espelho.enquadramento.aliquota_rat != null ? espelho.enquadramento.aliquota_rat.toFixed(2) : "—"}</div></div>
            <div><label className={labelCls}>FPAS (sugerido)</label><div className={roCls}>{espelho.enquadramento.codigo_fpas || "—"}</div></div>
          </div>
        )}
      </section>

      {/* Endereço (matriz) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Endereço (matriz)</h2>
        <div className="grid grid-cols-6 gap-4">
          <div className="col-span-2">
            <label className={labelCls}>CEP</label>
            <input className={inputCls} value={form.cep}
              onChange={(e) => { const v = maskCep(e.target.value); set("cep", v); if (v.replace(/\D/g, "").length === 8) buscarCep(v); }}
              onBlur={(e) => buscarCep(e.target.value)} maxLength={9} placeholder="00000-000" inputMode="numeric" />
            {cepMsg && <p className="text-[11px] text-amber-600 mt-1">{cepMsg}</p>}
          </div>
          <div className="col-span-4"><label className={labelCls}>Logradouro</label><input className={inputCls} value={form.endereco} onChange={(e) => set("endereco", e.target.value)} /></div>
          <div className="col-span-2"><label className={labelCls}>Número</label><input className={inputCls} value={form.numero} onChange={(e) => set("numero", e.target.value)} /></div>
          <div className="col-span-2"><label className={labelCls}>Complemento</label><input className={inputCls} value={form.complemento} onChange={(e) => set("complemento", e.target.value)} /></div>
          <div className="col-span-2"><label className={labelCls}>Bairro</label><input className={inputCls} value={form.bairro} onChange={(e) => set("bairro", e.target.value)} /></div>
          <div className="col-span-4"><label className={labelCls}>Cidade</label><input className={inputCls} value={form.cidade} onChange={(e) => set("cidade", e.target.value)} /></div>
          <div className="col-span-2"><label className={labelCls}>UF</label>
            <select className={inputCls} value={form.uf} onChange={(e) => set("uf", e.target.value)}>
              <option value="">—</option>{UFS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>
      </section>

      {/* Regime tributário por período (RF-0.156) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-gray-800">Regime tributário (por período)</h2>
          <button type="button" onClick={() => setRegimes((l) => [...l, { regime: "", inicio: form.periodo_inicio, fim: "" }])}
            className="text-[11px] text-teal-700 hover:underline">+ período</button>
        </div>
        {regimes.length === 0 && <p className="text-xs text-gray-500">Nenhum período. A empresa pode mudar de regime dentro da janela.</p>}
        {regimes.map((p, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-center">
            <select className={`${inputCls} col-span-4`} value={p.regime || ""} onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, regime: e.target.value } : x))}>
              <option value="">Regime…</option>{REGIMES.map((r) => <option key={r.v} value={r.v}>{r.label}</option>)}
            </select>
            {p.regime === "simples"
              ? <input className={`${inputCls} col-span-2`} placeholder="Anexo" value={p.anexo_simples || ""} onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, anexo_simples: e.target.value } : x))} />
              : <div className="col-span-2" />}
            <input type="month" className={`${inputCls} col-span-2`} value={p.inicio || ""} onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, inicio: e.target.value } : x))} />
            <input type="month" className={`${inputCls} col-span-3`} value={p.fim || ""} onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, fim: e.target.value } : x))} placeholder="fim (aberto)" />
            <button type="button" className="col-span-1 text-red-400 text-sm" onClick={() => setRegimes((l) => l.filter((_, j) => j !== i))}>✕</button>
          </div>
        ))}
      </section>

      {/* CPRB por período (RF-0.157/0.158) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-sm font-bold text-gray-800">CPRB — desoneração da folha (por período)</h2>
          <button type="button" onClick={() => setCprb((l) => [...l, { inicio: form.periodo_inicio, fim: "" }])}
            className="text-[11px] text-teal-700 hover:underline">+ período</button>
        </div>
        <p className="text-[11px] text-gray-400 mb-3">
          Opção anual (a empresa entra e sai). A partir de 01/2025 a CPRB <b>coexiste</b> com a cota patronal parcial
          (2025: 5% · 2026: 10% · 2027: 15% · 2028: 20%); RAT e Terceiros sempre devidos.
        </p>
        {cprb.length === 0 && <p className="text-xs text-gray-500">Sem períodos de CPRB.</p>}
        {cprb.map((p, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-center">
            <input type="month" className={`${inputCls} col-span-5`} value={p.inicio || ""} onChange={(e) => setCprb((l) => l.map((x, j) => j === i ? { ...x, inicio: e.target.value } : x))} />
            <input type="month" className={`${inputCls} col-span-5`} value={p.fim || ""} onChange={(e) => setCprb((l) => l.map((x, j) => j === i ? { ...x, fim: e.target.value } : x))} placeholder="fim (aberto)" />
            <button type="button" className="col-span-2 text-red-400 text-sm" onClick={() => setCprb((l) => l.filter((_, j) => j !== i))}>✕ remover</button>
          </div>
        ))}
      </section>

      {/* Contato + estabelecimentos */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Contato</h2>
        <div className="grid grid-cols-3 gap-4">
          <div><label className={labelCls}>Nome</label><input className={inputCls} value={form.contato_nome} onChange={(e) => set("contato_nome", e.target.value)} /></div>
          <div><label className={labelCls}>E-mail</label><input className={inputCls} value={form.contato_email} onChange={(e) => set("contato_email", e.target.value)} /></div>
          <div><label className={labelCls}>Telefone</label><input className={inputCls} value={form.contato_telefone} onChange={(e) => set("contato_telefone", e.target.value)} /></div>
        </div>
        <p className="text-[11px] text-gray-400 mt-3">Estabelecimentos ativos: <b>{numEstab}</b> (contagem automática).</p>
      </section>

      {msg && <p className={`text-sm mb-3 ${msg.includes("salvos") ? "text-emerald-600" : "text-red-600"}`}>{msg}</p>}
      <button onClick={salvar} disabled={salvando}
        className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
        {salvando ? "Salvando…" : "Salvar dados da empresa"}
      </button>
    </div>
  );
}
