// ==============================================================
// SST ESOCIAL GOV — Cadastro da Empresa (início do fluxo)
// Formulário que configura a empresa (CNAE, FPAS, regime) — desencadeia todo o cálculo.
// ==============================================================
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";

interface FpasOpcao { codigo: string; descricao: string; aliquota_terceiros: number; }

const REGIMES = [
  { v: "lucro_real", label: "Lucro Real" },
  { v: "lucro_presumido", label: "Lucro Presumido" },
  { v: "simples", label: "Simples Nacional" },
];

const UFS = [
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB",
  "PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
];

// Máscaras (exibem formatado; o estado guarda só dígitos)
const maskCnpj = (v: string) => {
  const d = (v || "").replace(/\D/g, "").slice(0, 14);
  return d
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
};
const maskCep = (v: string) => {
  const d = (v || "").replace(/\D/g, "").slice(0, 8);
  return d.replace(/^(\d{5})(\d)/, "$1-$2");
};

export function CadastroEmpresa() {
  const empresaId = useAuthStore((s) => s.user?.empresa_id);
  const [form, setForm] = useState<any>({
    razao_social: "", nome_fantasia: "", cnpj: "", cnae_principal: "",
    endereco: "", numero: "", complemento: "", bairro: "", cidade: "", uf: "", cep: "",
    regime_tributario: "", codigo_fpas: "", grau_risco: "", rat_aplicado: "",
    anexo_simples: "", apura_cprb: false, qtd_estabelecimentos: "",
    contato_nome: "", contato_email: "", contato_telefone: "",
  });
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState("");
  const [enq, setEnq] = useState<any>(null); // enquadramento oficial do CNAE (Anexo V)
  const [cepMsg, setCepMsg] = useState("");

  // carrega opções de FPAS
  const { data: fpasOpcoes } = useQuery<FpasOpcao[]>({
    queryKey: ["fpas-opcoes"],
    queryFn: () => apiClient.get("/empresas/opcoes/fpas").then((r) => r.data),
  });

  // carrega dados atuais da empresa
  useEffect(() => {
    if (!empresaId) return;
    apiClient.get(`/empresas/${empresaId}`).then((r) => {
      setForm((f: any) => ({ ...f, ...Object.fromEntries(
        Object.entries(r.data).filter(([, v]) => v !== null && v !== undefined)
      ) }));
    }).catch(() => {});
  }, [empresaId]);

  // Enquadramento automático: ao ter 7 dígitos no CNAE, busca o grau/RAT oficial (Anexo V).
  // Grau é FATO do CNAE → preenche sempre. RAT só preenche se vazio (o "aplicado hoje" pode
  // divergir do devido; essa divergência é o achado do Módulo 4, não pode ser mascarada).
  useEffect(() => {
    const c = (form.cnae_principal || "").replace(/\D/g, "");
    if (c.length !== 7) { setEnq(null); return; }
    let cancel = false;
    apiClient.get(`/cnae/${c}/enquadramento`).then((r) => {
      if (cancel) return;
      setEnq(r.data);
      setForm((f: any) => ({
        ...f,
        grau_risco: r.data.grau_risco,
        rat_aplicado: (f.rat_aplicado === "" || f.rat_aplicado == null) ? r.data.aliquota_rat : f.rat_aplicado,
        // FPAS é só sugestão por seção → pré-seleciona apenas se ainda estiver vazio
        codigo_fpas: ((f.codigo_fpas === "" || f.codigo_fpas == null) && r.data.fpas_sugerido)
          ? r.data.fpas_sugerido : f.codigo_fpas,
      }));
    }).catch((e) => {
      if (!cancel) setEnq({ erro: e?.response?.data?.detail || "CNAE não encontrado no Anexo V." });
    });
    return () => { cancel = true; };
  }, [form.cnae_principal]);

  const set = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  // Busca endereço pelo CEP (ViaCEP, roda no navegador). Preenche logradouro, bairro,
  // cidade e UF; o usuário completa só número e complemento.
  const buscarCep = async (cepRaw: string) => {
    const d = (cepRaw || "").replace(/\D/g, "");
    if (d.length !== 8) return;
    setCepMsg("Buscando endereço…");
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${d}/json/`);
      const data = await resp.json();
      if (data.erro) { setCepMsg("CEP não encontrado."); return; }
      setForm((f: any) => ({
        ...f,
        endereco: data.logradouro || f.endereco,
        bairro: data.bairro || f.bairro,
        cidade: data.localidade || f.cidade,
        uf: data.uf || f.uf,
      }));
      setCepMsg("");
    } catch {
      setCepMsg("Não foi possível buscar o CEP. Preencha manualmente.");
    }
  };

  const salvar = async () => {
    if (!empresaId) return;
    setSalvando(true); setMsg("");
    try {
      const payload: any = { ...form };
      // normaliza numéricos
      if (payload.grau_risco !== "") payload.grau_risco = Number(payload.grau_risco); else delete payload.grau_risco;
      if (payload.rat_aplicado !== "") payload.rat_aplicado = Number(payload.rat_aplicado); else delete payload.rat_aplicado;
      if (payload.qtd_estabelecimentos !== "") payload.qtd_estabelecimentos = Number(payload.qtd_estabelecimentos); else delete payload.qtd_estabelecimentos;
      await apiClient.put(`/empresas/${empresaId}`, payload);
      setMsg("Dados da empresa salvos com sucesso. O diagnóstico já pode ser calculado.");
    } catch {
      setMsg("Não foi possível salvar. Verifique os campos e tente novamente.");
    } finally {
      setSalvando(false);
    }
  };

  const inputCls = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-500";
  const labelCls = "block text-xs font-medium text-gray-600 mb-1";

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900">Cadastro da Empresa</h1>
      <p className="text-sm text-gray-500 mt-1 mb-6">
        Configure os dados da empresa. É o primeiro passo — o enquadramento (CNAE, FPAS, regime)
        desencadeia todo o cálculo de custeio.
      </p>

      {/* Identificação */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Identificação</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className={labelCls}>Razão social</label>
            <input className={inputCls} value={form.razao_social} onChange={(e) => set("razao_social", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Nome fantasia</label>
            <input className={inputCls} value={form.nome_fantasia} onChange={(e) => set("nome_fantasia", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>CNPJ</label>
            <input className={inputCls} value={maskCnpj(form.cnpj)}
              onChange={(e) => set("cnpj", e.target.value.replace(/\D/g, "").slice(0, 14))}
              maxLength={18} placeholder="00.000.000/0000-00" />
          </div>
        </div>
      </section>

      {/* Endereço (matriz) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Endereço (matriz)</h2>
        <div className="grid grid-cols-6 gap-4">
          <div className="col-span-2">
            <label className={labelCls}>CEP</label>
            <input className={inputCls} value={form.cep}
              onChange={(e) => { const v = maskCep(e.target.value); set("cep", v); if (v.replace(/\D/g, "").length === 8) buscarCep(v); }}
              onBlur={(e) => buscarCep(e.target.value)}
              maxLength={9} placeholder="00000-000" inputMode="numeric" />
            {cepMsg && <p className="text-[11px] text-amber-600 mt-1">{cepMsg}</p>}
          </div>
          <div className="col-span-4">
            <label className={labelCls}>Logradouro</label>
            <input className={inputCls} value={form.endereco} onChange={(e) => set("endereco", e.target.value)} placeholder="preenchido pelo CEP" />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Número</label>
            <input className={inputCls} value={form.numero} onChange={(e) => set("numero", e.target.value)} placeholder="nº" />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Complemento</label>
            <input className={inputCls} value={form.complemento} onChange={(e) => set("complemento", e.target.value)} placeholder="sala, bloco…" />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Bairro</label>
            <input className={inputCls} value={form.bairro} onChange={(e) => set("bairro", e.target.value)} placeholder="preenchido pelo CEP" />
          </div>
          <div className="col-span-4">
            <label className={labelCls}>Cidade</label>
            <input className={inputCls} value={form.cidade} onChange={(e) => set("cidade", e.target.value)} placeholder="preenchido pelo CEP" />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>UF</label>
            <select className={inputCls} value={form.uf} onChange={(e) => set("uf", e.target.value)}>
              <option value="">—</option>
              {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>
      </section>

      {/* Enquadramento */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Enquadramento previdenciário</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>CNAE principal (7 dígitos)</label>
            <input className={inputCls} value={form.cnae_principal} onChange={(e) => set("cnae_principal", e.target.value.replace(/\D/g, ""))} maxLength={7} />
          </div>
          <div>
            <label className={labelCls}>Código FPAS (define os Terceiros)</label>
            <select className={inputCls} value={form.codigo_fpas} onChange={(e) => set("codigo_fpas", e.target.value)}>
              <option value="">Selecione…</option>
              {fpasOpcoes?.map((o) => (
                <option key={o.codigo} value={o.codigo}>
                  {o.codigo} — {o.descricao} ({o.aliquota_terceiros.toFixed(2)}%)
                </option>
              ))}
            </select>
            {enq && !enq.erro && enq.fpas_sugerido && (
              <p className="text-[11px] text-amber-600 mt-1">
                Sugerido pelo CNAE ({enq.fpas_setor}): FPAS {enq.fpas_sugerido}. Confirme conforme a atividade.
              </p>
            )}
          </div>
          <div>
            <label className={labelCls}>Regime tributário</label>
            <select className={inputCls} value={form.regime_tributario} onChange={(e) => set("regime_tributario", e.target.value)}>
              <option value="">Selecione…</option>
              {REGIMES.map((r) => <option key={r.v} value={r.v}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label className={labelCls}>Grau de risco (1 a 3 — definido pelo CNAE)</label>
            <input type="number" min={1} max={3} className={inputCls} value={form.grau_risco} onChange={(e) => set("grau_risco", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>RAT aplicado hoje (%)</label>
            <input type="number" step="0.01" className={inputCls} value={form.rat_aplicado} onChange={(e) => set("rat_aplicado", e.target.value)} placeholder="ex: 3.00" />
          </div>
          {enq && (
            <div className="col-span-2">
              {enq.erro ? (
                <p className="text-xs text-amber-600">⚠ {enq.erro}</p>
              ) : (
                <div className="rounded-lg bg-teal-50 border border-teal-200 px-3 py-2 text-xs text-teal-900">
                  <span className="font-semibold">Enquadramento oficial (CNAE {enq.cnae_fmt}):</span>{" "}
                  {enq.descricao} — grau <b>{enq.grau_label}</b> ({enq.grau_risco}), <b>RAT devido {enq.aliquota_rat.toFixed(0)}%</b>.
                  <br />
                  <span className="text-teal-700">Fonte: {enq.fonte}. O "RAT aplicado hoje" acima pode ser ajustado se a empresa recolhe outro valor — a diferença vira achado.</span>
                </div>
              )}
            </div>
          )}
          <div>
            <label className={labelCls}>Número de estabelecimentos (matriz + filiais/obras)</label>
            <input type="number" min={1} className={inputCls} value={form.qtd_estabelecimentos} onChange={(e) => set("qtd_estabelecimentos", e.target.value)} placeholder="ex: 3" />
          </div>
          <div className="flex items-center gap-2 mt-6">
            <input type="checkbox" checked={!!form.apura_cprb} onChange={(e) => set("apura_cprb", e.target.checked)} id="cprb" />
            <label htmlFor="cprb" className="text-sm text-gray-700">Apura CPRB (desoneração da folha)</label>
          </div>
        </div>
      </section>

      {/* Contato */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Contato</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className={labelCls}>Nome</label>
            <input className={inputCls} value={form.contato_nome} onChange={(e) => set("contato_nome", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>E-mail</label>
            <input className={inputCls} value={form.contato_email} onChange={(e) => set("contato_email", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Telefone</label>
            <input className={inputCls} value={form.contato_telefone} onChange={(e) => set("contato_telefone", e.target.value)} />
          </div>
        </div>
      </section>

      {msg && <p className={`text-sm mb-3 ${msg.includes("sucesso") ? "text-emerald-600" : "text-red-600"}`}>{msg}</p>}

      <button onClick={salvar} disabled={salvando}
        className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
        {salvando ? "Salvando…" : "Salvar dados da empresa"}
      </button>
    </div>
  );
}
