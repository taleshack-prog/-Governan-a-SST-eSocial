// ==============================================================
// SST ESOCIAL GOV — Cadastro da Empresa (Adendo 03, v1)
// O enquadramento é do ESTABELECIMENTO (matriz), não da empresa (RN-17). Esta tela guarda
// identificação, período de apuração, regime/CPRB por período e contato; o enquadramento
// aparece como espelho read-only da matriz.
// ==============================================================
import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";
import { Fundamentacao } from "../components/Fundamentacao";
import * as fmt from "../utils/formato";

// Item 5: dado derivado se apresenta como VALOR, não como caixa de entrada. Sem borda e sem
// fundo de input — a diferença entre "isto você preenche" e "isto o sistema calculou" precisa
// ser evidente sem que ninguém leia a legenda do cadeado.
const derivLabel = "block text-[11px] text-gray-500";
const derivVal = "text-lg font-semibold text-gray-900 tabular-nums leading-tight";

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

interface Periodo { regime?: string; anexo_simples?: string; inicio: string; fim: string; fim_aberto?: boolean; }
type CprbStatus = "nao_informado" | "nao_optante" | "optante";

// Nomes legíveis dos campos rastreados, para a dica de procedência não mostrar nome de coluna.
const ROTULO_CAMPO: Record<string, string> = {
  razao_social: "razão social", nome_fantasia: "nome fantasia", cnae_principal: "CNAE principal",
  data_abertura: "data de abertura", data_encerramento: "data de encerramento",
  endereco: "logradouro", numero: "número", complemento: "complemento", bairro: "bairro",
  cidade: "cidade", uf: "UF", cep: "CEP",
};
const rotuloCampo = (c: string) => ROTULO_CAMPO[c] || c;

// Item 3: procedência POR CAMPO, em texto — não só por cor. O mesmo padrão que já existia no
// rótulo da data de abertura, agora alimentado pelo mapa que o backend grava, campo a campo.
// Cor sozinha não carrega a informação: num laudo, a origem precisa estar escrita.
// Três procedências, com pesos visuais diferentes de propósito:
//   consultado — o caso normal. Cinza, peso normal: não deve competir por atenção.
//   declarado  — a EXCEÇÃO. Azul e mais forte, para o olho achar no meio de sete campos.
//   alterado   — veio da Receita e foi editado. Âmbar: é o caso de maior peso jurídico,
//                porque a divergência entre o consultado e o declarado é ela própria um achado.
function procedenciaDe(mapa: any, campo: string) {
  const e = mapa?.[campo];
  if (!e?.origem) return null;
  if (e.origem === "consultado") return { tipo: "consultado" as const, entrada: e };
  const tipo: "alterado" | "declarado" = e.valor_consultado ? "alterado" : "declarado";
  return { tipo, entrada: e };
}

function Procedencia({ mapa, campo, genero = "a" }: { mapa: any; campo: string; genero?: "a" | "o" }) {
  const p = procedenciaDe(mapa, campo);
  if (!p) return null;
  const { tipo, entrada } = p;
  return (
    <span
      className={`ml-1 ${tipo === "declarado" ? "text-blue-600 font-semibold"
        : tipo === "alterado" ? "text-amber-700 font-semibold" : "text-gray-400 font-normal"}`}
      title={tipo === "alterado" ? `Veio da consulta como "${entrada.valor_consultado}" e foi alterado à mão.` : undefined}>
      {tipo === "consultado" ? `(consultad${genero})`
        : tipo === "alterado" ? `(alterad${genero} — consultad${genero}: ${entrada.valor_consultado})`
        : "(declarado)"}
    </span>
  );
}

// O fundo do campo acompanha a cor do marcador. Sozinha, a cor é um código sem legenda;
// sozinho, o rótulo não se destaca no meio de sete campos. Os dois juntos é que resolvem.
function fundoProcedencia(mapa: any, campo: string, base: string) {
  const p = procedenciaDe(mapa, campo);
  if (!p || p.tipo === "consultado") return base;
  return `${base} ${p.tipo === "declarado" ? "bg-blue-50 border-blue-200" : "bg-amber-50 border-amber-200"}`;
}

// Situação da competência no espelho (espelha api/services/enquadramento_situacao.py)
const ESP_SIT: Record<string, string> = {
  conferencia: "conferência", apurado: "apurado (falta o aplicado)", conferido: "conferido",
};

// RF-0.164/0.165/0.166: valida um período de CPRB no front (espelho do backend). Devolve "" se ok.
const CPRB_FIM_LIMITE = "2027-12";
const validaCprbPeriodo = (p: Periodo, abertura: string, encerramento: string): string => {
  if (!p.inicio) return "Informe o início do período de CPRB.";
  const [ya, ma] = p.inicio.split("-").map(Number);
  const abreComp = (abertura || "").slice(0, 7), encComp = (encerramento || "").slice(0, 7);
  if (ma !== 1 && p.inicio !== abreComp)
    return `Opção anual: o período deve iniciar em janeiro (ou na abertura da empresa). Início ${p.inicio}.`;
  if (`${ya}-${String(ma).padStart(2, "0")}` > CPRB_FIM_LIMITE)
    return "CPRB extinta em 2028: início não pode ultrapassar 12/2027.";
  const fim = p.fim || (p.fim_aberto ? "" : `${ya}-12`);   // sem fim e sem "em aberto" → fecha em dez do ano
  if (fim) {
    if (fim < p.inicio) return "Fim anterior ao início.";
    const [, mf] = fim.split("-").map(Number);
    if (mf !== 12 && fim !== encComp)
      return `Opção anual: o período deve terminar em dezembro (ou no encerramento da empresa). Fim ${fim}.`;
    if (fim > CPRB_FIM_LIMITE) return "CPRB extinta em 2028: nenhum período pode ultrapassar 12/2027.";
  }
  return "";
};

// RF-0.156: regime não pode ter lacuna dentro do período de apuração. Devolve "" se ok.
const proxMes = (ym: string) => { const [y, m] = ym.split("-").map(Number); return m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, "0")}`; };
const validaRegime = (regimes: Periodo[], pIni: string, pFim: string): string => {
  if (!pIni || !pFim) return "";
  for (const r of regimes) {
    if (!r.regime && r.inicio) return "Há período de regime sem o regime selecionado.";
    if (r.regime && !r.inicio) return "Há regime sem data de início.";
    if (r.regime === "simples" && !r.anexo_simples) return "Simples Nacional exige o anexo.";
    if (r.inicio && r.fim && r.fim < r.inicio) return "Período de regime com fim anterior ao início.";
  }
  const validos = regimes.filter((r) => r.regime && r.inicio);
  if (validos.length === 0) return `Declare o regime tributário para o período de apuração (${pIni} a ${pFim}).`;
  // varre mês a mês a janela de apuração procurando o primeiro mês descoberto
  let m = pIni;
  while (m <= pFim) {
    const coberto = validos.some((r) => r.inicio <= m && (!r.fim || r.fim >= m));
    if (!coberto) return `Lacuna de regime em ${m}: todo o período de apuração precisa estar coberto.`;
    m = proxMes(m);
  }
  return "";
};

export function CadastroEmpresa() {
  const empresaId = useAuthStore((s) => s.user?.empresa_id);
  const [form, setForm] = useState<any>({
    razao_social: "", nome_fantasia: "", cnpj: "", cnae_principal: "",
    situacao_cadastral: "", situacao_cadastral_data: "", situacao_cadastral_em: "",
    periodo_inicio: ymMinus(59), periodo_fim: ymToday(),
    data_abertura: "", data_encerramento: "",
    endereco: "", numero: "", complemento: "", bairro: "", cidade: "", uf: "", cep: "",
    contato_nome: "", contato_email: "", contato_telefone: "",
  });
  const [origem, setOrigem] = useState<string>("");          // consultado | declarado
  const [consultaBruta, setConsultaBruta] = useState<Record<string, string | null> | null>(null);
  const [resumoOrigem, setResumoOrigem] = useState<any>(null);   // composição real, vinda do backend
  const [camposOrigem, setCamposOrigem] = useState<any>({});     // procedência campo a campo
  const [arquivada, setArquivada] = useState(false);
  const [mostrarExclusao, setMostrarExclusao] = useState(false);
  const [confirmaExclusao, setConfirmaExclusao] = useState("");
  const [consultadoEm, setConsultadoEm] = useState<string>("");
  const [cnaeDescricao, setCnaeDescricao] = useState<string>("");   // descrição da subclasse (Anexo I)
  const [secundarios, setSecundarios] = useState<any[]>([]);
  const [regimes, setRegimes] = useState<Periodo[]>([]);
  const [cprb, setCprb] = useState<Periodo[]>([]);
  const [cprbStatus, setCprbStatus] = useState<CprbStatus>("nao_informado");
  const [cprbVerif, setCprbVerif] = useState<{ por?: string; em?: string }>({});
  const [espelho, setEspelho] = useState<any>(null);
  const [numEstab, setNumEstab] = useState<number>(0);
  const [cnpjErro, setCnpjErro] = useState("");
  const [consultaMsg, setConsultaMsg] = useState("");
  const [cepMsg, setCepMsg] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState("");

  const set = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  // Item 1 da revisão de 20/10: a linha de procedência não atualizava depois de salvar.
  // CAUSA: o carregamento da empresa só acontecia na montagem da tela. Ao salvar, o código relia
  // a empresa mas aproveitava APENAS num_estabelecimentos e jogava fora resumo_origem — então a
  // linha continuava exibindo o estado de quando a página foi aberta, enquanto a situação
  // cadastral logo ao lado, que vive no formulário, já mostrava a consulta nova. Duas
  // informações da mesma consulta divergindo na mesma tela.
  // CORREÇÃO: o carregamento vira função e é chamado também depois de salvar. A tela passa a
  // exibir o que FOI GRAVADO, não o que o navegador supõe — que é o que o laudo cita.
  const carregarEmpresa = () => {
    if (!empresaId) return Promise.resolve();
    return apiClient.get(`/empresas/${empresaId}`).then((r) => {
      const d = r.data;
      setForm((f: any) => ({
        ...f,
        razao_social: d.razao_social ?? "", nome_fantasia: d.nome_fantasia ?? "",
        situacao_cadastral: d.situacao_cadastral ?? "", situacao_cadastral_data: d.situacao_cadastral_data ?? "", situacao_cadastral_em: d.situacao_cadastral_em ?? "",
        cnpj: d.cnpj ?? "", cnae_principal: d.cnae_principal ?? "",
        periodo_inicio: dateToYm(d.periodo_apuracao_inicio) || f.periodo_inicio,
        periodo_fim: dateToYm(d.periodo_apuracao_fim) || f.periodo_fim,
        data_abertura: d.data_abertura ?? "", data_encerramento: d.data_encerramento ?? "",
        endereco: d.endereco ?? "", numero: d.numero ?? "", complemento: d.complemento ?? "",
        bairro: d.bairro ?? "", cidade: d.cidade ?? "", uf: d.uf ?? "", cep: d.cep ?? "",
        contato_nome: d.contato_nome ?? "", contato_email: d.contato_email ?? "", contato_telefone: d.contato_telefone ?? "",
      }));
      setOrigem(d.origem_cadastro ?? "");
      setResumoOrigem(d.resumo_origem ?? null);
      setCamposOrigem(d.campos_origem ?? {});
      setArquivada(!!d.arquivada);
      setConsultadoEm(d.consultado_em ?? "");
      setCnaeDescricao(d.cnae_principal_descricao ?? "");
      setSecundarios(d.cnaes_secundarios ?? []);
      setNumEstab(d.num_estabelecimentos ?? 0);
    }).catch(() => {});
  };

  // carrega empresa + regime + cprb + espelho
  useEffect(() => {
    if (!empresaId) return;
    carregarEmpresa();
    apiClient.get(`/empresas/${empresaId}/regime`).then((r) => setRegimes(
      (r.data || []).map((p: any) => ({ regime: p.regime, anexo_simples: p.anexo_simples, inicio: dateToYm(p.inicio), fim: dateToYm(p.fim) }))
    )).catch(() => {});
    apiClient.get(`/empresas/${empresaId}/cprb`).then((r) => {
      const d = r.data || {};
      setCprbStatus((d.status as CprbStatus) || "nao_informado");
      setCprb((d.periodos || []).map((p: any) => ({ inicio: dateToYm(p.inicio), fim: dateToYm(p.fim), fim_aberto: !p.fim })));
      setCprbVerif({ por: d.verificado_por, em: d.verificado_em });
    }).catch(() => {});
    carregarEspelho();
  }, [empresaId]);

  const carregarEspelho = () => {
    if (!empresaId) return;
    // Nunca engolir o erro: antes um 500 aqui caía no texto de "aparece depois", e o espelho
    // parecia apenas não implementado. Agora a falha aparece na tela.
    apiClient.get(`/empresas/${empresaId}/matriz-enquadramento`)
      .then((r) => setEspelho(r.data))
      .catch((e) => setEspelho({ erro: e?.response?.data?.detail || "Não foi possível ler o enquadramento da matriz." }));
  };

  // Consulta de CNPJ pelo backend (RF-0.150)
  const consultarCnpj = async () => {
    const d = (form.cnpj || "").replace(/\D/g, "");
    if (!validaCnpj(d)) { setCnpjErro("CNPJ inválido (dígito verificador)."); return; }
    setCnpjErro(""); setConsultaMsg("Consultando dados públicos…");
    try {
      const r = await apiClient.get(`/empresas/consulta-cnpj/${d}`);
      const x = r.data;
      // A consulta devolve STRING VAZIA (não null) para o que a Receita não tem — nome fantasia,
      // número, complemento. Com `??` o vazio passava e apagava o que o usuário tinha digitado.
      // Aqui vazio é ausência: mantém o que já está no formulário.
      const ou = (novo: any, atual: any) => (novo === null || novo === undefined || String(novo).trim() === "" ? atual : novo);
      setForm((f: any) => ({
        ...f,
        razao_social: ou(x.razao_social, f.razao_social),
        nome_fantasia: ou(x.nome_fantasia, f.nome_fantasia),
        cnae_principal: ou(x.cnae_principal, f.cnae_principal),
        endereco: ou(x.logradouro, f.endereco), numero: ou(x.numero, f.numero),
        complemento: ou(x.complemento, f.complemento), bairro: ou(x.bairro, f.bairro),
        cidade: ou(x.municipio, f.cidade), uf: ou(x.uf, f.uf), cep: ou(x.cep, f.cep),
        data_abertura: ou(x.data_abertura, f.data_abertura),
        // Item 8: a situação deixa de morrer na mensagem e vira campo do registro
        situacao_cadastral: x.situacao_cadastral ?? f.situacao_cadastral,
        situacao_cadastral_data: x.situacao_cadastral_data ?? f.situacao_cadastral_data,
        // UMA consulta, UM horário. Antes este campo carimbava o relógio do NAVEGADOR enquanto a
        // procedência carimbava o do SERVIDOR — duas horas diferentes para o mesmo ato, e a do
        // navegador pode estar errada. O laudo cita as duas; elas não podem divergir.
        situacao_cadastral_em: x.consultado_em || new Date().toISOString(),
      }));
      // Item 1: guarda EXATAMENTE o que a consulta devolveu, por campo. É enviado no salvamento
      // para o backend decidir a origem comparando com o valor gravado — a tela não afirma
      // origem, só reporta o que recebeu.
      setConsultaBruta({
        razao_social: x.razao_social ?? null, nome_fantasia: x.nome_fantasia ?? null,
        cnae_principal: x.cnae_principal ?? null, data_abertura: x.data_abertura ?? null,
        endereco: x.logradouro ?? null, numero: x.numero ?? null, complemento: x.complemento ?? null,
        bairro: x.bairro ?? null, cidade: x.municipio ?? null, uf: x.uf ?? null, cep: x.cep ?? null,
      });
      setSecundarios(x.cnaes_secundarios || []);
      setCnaeDescricao(x.cnae_principal_descricao || "");
      setOrigem("consultado");
      setConsultadoEm(x.consultado_em || new Date().toISOString());
      setConsultaMsg("Consultado na Receita. Revise e confirme — o dado vale após salvar.");
    } catch (e: any) {
      setOrigem("declarado");
      setConsultaMsg(`${e?.response?.data?.detail || "Consulta indisponível"}. Preencha manualmente (origem: declarado).`);
    }
  };

  // CNAE digitado à mão: a descrição anterior passa a ser MENTIRA no instante da edição — ficaria
  // "Comércio varejista" ao lado de um código de construção. Então ela sai da tela na hora e só
  // volta resolvida pelo Anexo I, a mesma tabela de onde sai o grau de risco. Código fora do
  // Anexo I fica sem descrição: é a mesma ausência que manda a competência à conferência.
  const resolverDescricaoCnae = async (codigo: string) => {
    if ((codigo || "").length !== 7) { setCnaeDescricao(""); return; }
    try {
      const r = await apiClient.get(`/cnae/${codigo}`);
      setCnaeDescricao(r.data?.descricao || "");
    } catch { setCnaeDescricao(""); }
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
    // RF-0.156: regime sem lacuna no período de apuração
    const errRegime = validaRegime(regimes, form.periodo_inicio, form.periodo_fim);
    if (errRegime) { setMsg(`Regime — ${errRegime}`); return; }
    // RF-0.163..0.166: valida o bloco CPRB antes de enviar
    if (cprbStatus === "optante") {
      if (cprb.length === 0) { setMsg("Optante pela CPRB: informe ao menos um período."); return; }
      for (const p of cprb) {
        const err = validaCprbPeriodo(p, form.data_abertura, form.data_encerramento);
        if (err) { setMsg(`CPRB — ${err}`); return; }
      }
    }
    setSalvando(true); setMsg("");
    try {
      await apiClient.put(`/empresas/${empresaId}`, {
        razao_social: form.razao_social, nome_fantasia: form.nome_fantasia, cnpj: form.cnpj,
        cnae_principal: form.cnae_principal || null,
        periodo_apuracao_inicio: ymToDate(form.periodo_inicio), periodo_apuracao_fim: ymToDate(form.periodo_fim),
        data_abertura: form.data_abertura || null, data_encerramento: form.data_encerramento || null,
        origem_cadastro: origem || "declarado",
        // consultado_em e campos_consultados viajam JUNTOS, e só quando houve consulta nesta
        // sessão de edição. Antes, salvar sem consultar mandava consultado_em: null e APAGAVA a
        // data da consulta anterior — perdendo o registro de um ato que de fato ocorreu. Omitir a
        // chave (exclude_unset no backend) preserva o que está gravado.
        ...(consultaBruta ? { campos_consultados: consultaBruta, consultado_em: consultadoEm || null } : {}),
        situacao_cadastral: form.situacao_cadastral || null,
        situacao_cadastral_data: form.situacao_cadastral_data || null,
        situacao_cadastral_em: form.situacao_cadastral_em || null,
        cnaes_secundarios: secundarios.map((c: any) => c.codigo).filter(Boolean),
        endereco: form.endereco, numero: form.numero, complemento: form.complemento,
        bairro: form.bairro, cidade: form.cidade, uf: form.uf, cep: form.cep,
        contato_nome: form.contato_nome, contato_email: form.contato_email, contato_telefone: form.contato_telefone,
      });
      await apiClient.put(`/empresas/${empresaId}/regime`, regimes.filter((p) => p.regime && p.inicio).map((p) => ({
        regime: p.regime, anexo_simples: p.regime === "simples" ? (p.anexo_simples || null) : null,
        inicio: ymToDate(p.inicio), fim: p.fim ? ymToDate(p.fim) : null,
      })));
      await apiClient.put(`/empresas/${empresaId}/cprb`, {
        status: cprbStatus,
        periodos: cprbStatus === "optante"
          ? cprb.filter((p) => p.inicio).map((p) => ({
              inicio: ymToDate(p.inicio),
              fim: p.fim_aberto ? null : (p.fim ? ymToDate(p.fim) : null),
              fim_confirmado: !!p.fim_aberto,   // RF-0.166: "em aberto" é a confirmação explícita
            }))
          : [],
      });
      setConsultaMsg("");   // transitório: cumpriu a função, sai de cena
      setMsg("Dados salvos. A matriz foi criada/atualizada e o enquadramento espelhado abaixo.");
      carregarEspelho();
      // Relê a empresa INTEIRA: procedência por campo, resumo, consultado_em e descrição do CNAE
      // passam a refletir o que foi gravado. Antes esta chamada existia e aproveitava só a
      // contagem de estabelecimentos — a linha de procedência ficava congelada até recarregar a
      // página, que é o defeito do item 1.
      carregarEmpresa();
      // A consulta desta sessão já foi gravada; zerar evita reenviá-la como se fosse nova.
      setConsultaBruta(null);
      apiClient.get(`/empresas/${empresaId}/cprb`).then((r) => setCprbVerif({ por: r.data?.verificado_por, em: r.data?.verificado_em })).catch(() => {});
    } catch {
      setMsg("Não foi possível salvar. Verifique os campos (períodos não podem se sobrepor).");
    } finally { setSalvando(false); }
  };

  // RF-0.207: arquivar é REVERSÍVEL e preserva tudo; excluir é IRREVERSÍVEL e exige a razão
  // social digitada. A ação antiga ("Zerar empresa") apagava enquadramento apurado a um clique,
  // sem volta — saiu do sistema junto com o endpoint.
  const arquivar = async () => {
    if (!empresaId) return;
    setSalvando(true); setMsg("");
    try {
      const r = await apiClient.post(`/empresas/${empresaId}/arquivar`);
      setArquivada(true);
      setMsg(r.data?.mensagem || "Empresa arquivada.");
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || "Não foi possível arquivar.");
    } finally { setSalvando(false); }
  };

  const desarquivar = async () => {
    if (!empresaId) return;
    setSalvando(true); setMsg("");
    try {
      await apiClient.post(`/empresas/${empresaId}/desarquivar`);
      setArquivada(false);
      setMsg("Empresa restaurada à lista principal.");
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || "Não foi possível restaurar.");
    } finally { setSalvando(false); }
  };

  const excluir = async () => {
    if (!empresaId) return;
    setSalvando(true); setMsg("");
    try {
      // A razão social digitada vai no corpo; o backend compara com a cadastrada e recusa se
      // não for idêntica. A confirmação é do servidor, não da tela.
      await apiClient.delete(`/empresas/${empresaId}`, { data: { razao_social: confirmaExclusao } });
      setMsg("Empresa excluída. Cadastre a próxima pelo CNPJ.");
      setConfirmaExclusao(""); setMostrarExclusao(false);
      window.location.reload();
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || "Não foi possível excluir.");
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
            {/* AVISO TRANSITÓRIO da consulta recém-executada. Some ao salvar — é recado de
                operação, não procedência. Antes, este aviso e o rótulo permanente ficavam
                empilhados dizendo quase a mesma coisa, com funções distintas sobrepostas. */}
            {consultaMsg && (
              <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-1">
                {consultaMsg}
              </p>
            )}
            {/* RÓTULO PERMANENTE de procedência, com a composição real do registro. "consultado"
                no singular, num cadastro com campo digitado, é afirmação falsa — e a memória de
                enquadramento cita a procedência dos dados. */}
            {(resumoOrigem?.consultado_em || origem) && (
              <p className="text-[11px] text-gray-500 mt-1">
                {resumoOrigem?.consultado_em
                  ? <>Consultado em <b>{fmt.dataHora(resumoOrigem.consultado_em)}</b></>
                  : <>Sem consulta registrada — cadastro <b>declarado</b></>}
                {resumoOrigem?.campos_alterados?.length > 0 && (
                  <span className="text-amber-700" title={`Vieram da consulta e foram editados: ${resumoOrigem.campos_alterados.map(rotuloCampo).join(", ")}`}>
                    {" · "}{resumoOrigem.campos_alterados.length} campo
                    {resumoOrigem.campos_alterados.length > 1 ? "s" : ""} alterado
                    {resumoOrigem.campos_alterados.length > 1 ? "s" : ""} manualmente
                  </span>
                )}
                {resumoOrigem?.campos_declarados?.length > 0 && (
                  <span title={`Nunca vieram da consulta: ${resumoOrigem.campos_declarados.map(rotuloCampo).join(", ")}`}>
                    {" · "}{resumoOrigem.campos_declarados.length} preenchido
                    {resumoOrigem.campos_declarados.length > 1 ? "s" : ""} à mão
                  </span>
                )}
                .
              </p>
            )}
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
            <label className={labelCls}>Razão social<Procedencia mapa={camposOrigem} campo="razao_social" /></label>
            <input className={fundoProcedencia(camposOrigem, "razao_social", inputCls)}
              value={form.razao_social} onChange={(e) => set("razao_social", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Nome fantasia<Procedencia mapa={camposOrigem} campo="nome_fantasia" genero="o" /></label>
            <input className={fundoProcedencia(camposOrigem, "nome_fantasia", inputCls)}
              value={form.nome_fantasia} onChange={(e) => set("nome_fantasia", e.target.value)} />
          </div>
          {/* As TRÊS datas que delimitam a janela de apuração ficam juntas de propósito:
              abertura, encerramento e situação cadastral. Empresa baixada, suspensa ou inapta
              limita a janela do mesmo modo que a encerrada. */}
          <div className="col-span-2 grid grid-cols-3 gap-4">
            <div>
              <label className={labelCls}>Data de abertura<Procedencia mapa={camposOrigem} campo="data_abertura" /></label>
              <input type="date" className={fundoProcedencia(camposOrigem, "data_abertura", inputCls)}
                value={form.data_abertura || ""} onChange={(e) => set("data_abertura", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Data de encerramento (se houver)<Procedencia mapa={camposOrigem} campo="data_encerramento" /></label>
              <input type="date" className={fundoProcedencia(camposOrigem, "data_encerramento", inputCls)}
                value={form.data_encerramento || ""} onChange={(e) => set("data_encerramento", e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>
                Situação cadastral
                {/* SEM (§), de propósito. Situação cadastral é FATO do cadastro da Receita, não
                    número que decorra de norma — o marcador certo é "(consultada)", que é o que
                    ela é. O § precisa significar uma coisa só, "este valor vem de uma norma,
                    clique para ver qual", senão perde o valor nos campos do enquadramento, onde
                    ele é a prova de que o número veio de norma vigente. */}
                {form.situacao_cadastral && <span className="ml-1 text-gray-400 font-normal">(consultada)</span>}
              </label>
              {form.situacao_cadastral ? (
                <>
                  {/* VALOR, não caixa de digitação: vem da Receita e ninguém deve poder digitar.
                      ATIVA recebe tratamento NEUTRO — é o estado normal e não deve gritar. Quem
                      precisa de destaque é BAIXADA, SUSPENSA ou INAPTA: são essas que mudam a
                      janela, e pintar a ATIVA tiraria o valor do alerta justamente nos casos
                      em que ele importa. */}
                  <div className="mt-1">
                    <span className={`inline-block px-2.5 py-1 rounded text-sm font-semibold tracking-wide ${
                      /ATIVA/i.test(form.situacao_cadastral)
                        ? "bg-gray-100 text-gray-700"
                        : "bg-red-50 text-red-700 border border-red-200"}`}>
                      {form.situacao_cadastral}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-400 mt-1">
                    {form.situacao_cadastral_data && <>Desde {fmt.data(form.situacao_cadastral_data)} · </>}
                    {form.situacao_cadastral_em ? <>Apurada em {fmt.dataHora(form.situacao_cadastral_em)}</> : "—"}
                  </p>
                  {!/ATIVA/i.test(form.situacao_cadastral) && !form.situacao_cadastral_data && (
                    <p className="text-[11px] text-amber-700 mt-1">
                      Sem data da situação: a janela não pode ser delimitada e as competências vão à conferência.
                    </p>
                  )}
                </>
              ) : (
                <div className="mt-1 text-sm text-gray-400 py-1">Consulte o CNPJ para obter.</div>
              )}
            </div>
          </div>
          <div className="col-span-2">
            <label className={labelCls}>CNAE principal<Procedencia mapa={camposOrigem} campo="cnae_principal" genero="o" /></label>
            <input className={`${fundoProcedencia(camposOrigem, "cnae_principal", inputCls)} font-mono`}
              value={fmt.cnaeParcial(form.cnae_principal)} maxLength={10}
              onChange={(e) => {
                const d = e.target.value.replace(/\D/g, "").slice(0, 7);
                set("cnae_principal", d);
                resolverDescricaoCnae(d);
              }}
              placeholder="0000-0/00" inputMode="numeric" />
            {/* Item 3: a descrição transforma um código, que só especialista confere, numa frase
                que qualquer um confere — inclusive o cliente, que conhece o próprio negócio. */}
            {cnaeDescricao && (
              <p className="text-[11px] text-gray-500 mt-1">{fmt.cnae(form.cnae_principal)} — {cnaeDescricao}</p>
            )}
          </div>
        </div>
        {/* Nos secundários vai só o código: cinco descrições viram um parágrafo. A descrição fica
            no hover de cada um. */}
        {secundarios.length > 0 && (
          <p className="text-[11px] text-gray-400 mt-2">
            CNAEs secundários:{" "}
            {secundarios.map((c: any, i: number) => (
              <span key={c.codigo}>
                {i > 0 && ", "}
                <span className={c.descricao ? "underline decoration-dotted cursor-help" : undefined}
                  title={c.descricao || undefined}>{fmt.cnae(c.codigo)}</span>
              </span>
            ))}.
          </p>
        )}
      </section>

      {/* Espelho do enquadramento da matriz (RF-0.155) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-sm font-bold text-gray-800">Enquadramento da matriz</h2>
          <a href="/estabelecimentos" className="text-[11px] text-teal-700 hover:underline">editar em Estabelecimentos →</a>
        </div>
        <p className="text-[11px] text-gray-400 mb-3">🔒 pertence ao estabelecimento matriz — somente leitura aqui (RN-17).</p>
        {espelho?.erro ? (
          <p className="text-xs text-red-500">{espelho.erro}</p>
        ) : espelho === null ? (
          <p className="text-xs text-gray-400">Carregando…</p>
        ) : !espelho?.existe ? (
          <p className="text-xs text-gray-500">A matriz é criada ao salvar o cadastro.</p>
        ) : !espelho?.enquadramento ? (
          <p className="text-xs text-gray-500">{espelho.motivo || "Enquadramento ainda não disponível."}</p>
        ) : (
          <>
            {/* Item 7: o espelho mostra UMA competência de sessenta. Essa frase vem antes dos
                números, não em letra miúda embaixo — na mesma empresa um ano pode ser crédito
                e outro, passivo. */}
            <div className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 mb-4">
              <p className="text-xs text-gray-700">
                {espelho.enquadramento.competencia ? (
                  <>
                    Competência <b>{fmt.competencia(espelho.enquadramento.competencia)}</b>
                    {espelho.serie_resumo?.total ? <>, de {espelho.serie_resumo.total} analisadas</> : null}
                    {espelho.serie_resumo ? (
                      <> — {espelho.serie_resumo.conferidas} conferidas
                        {espelho.serie_resumo.apuradas > 0 && <>, {espelho.serie_resumo.apuradas} sem o aplicado</>}
                        {espelho.serie_resumo.em_conferencia > 0 && <>, {espelho.serie_resumo.em_conferencia} em conferência</>}
                      </>
                    ) : null}
                  </>
                ) : (
                  <>Prévia — a série mensal ainda não foi apurada.</>
                )}
              </p>
              <a href="/estabelecimentos" className="text-xs text-teal-700 hover:underline whitespace-nowrap">
                Ver enquadramento completo →
              </a>
            </div>

            {/* Item 5: dado derivado é VALOR, não caixa de entrada. Sem moldura de input, para
                ninguém tentar corrigir à mão o número que o sistema existe para calcular. */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-4">
              <div>
                <span className={derivLabel}>CNAE preponderante<Fundamentacao campo="atividade_preponderante" /></span>
                <div className={`${derivVal} font-mono`}>{fmt.cnae(espelho.enquadramento.cnae)}</div>
                {espelho.enquadramento.cnae_descricao && (
                  <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">{espelho.enquadramento.cnae_descricao}</p>
                )}
              </div>
              <div>
                <span className={derivLabel}>Grau de risco<Fundamentacao campo="rat_devido" /></span>
                <div className={derivVal}>
                  {espelho.enquadramento.grau_risco
                    ? <>{espelho.enquadramento.grau_risco}<span className="text-sm font-normal text-gray-500"> — {espelho.enquadramento.grau_label}</span></>
                    : "—"}
                </div>
              </div>
              <div>
                <span className={derivLabel}>RAT devido<Fundamentacao campo="rat_devido" /></span>
                <div className={derivVal}>{fmt.pct(espelho.enquadramento.aliquota_rat)}</div>
              </div>
              <div>
                <span className={derivLabel}>RAT aplicado<Fundamentacao campo="rat_aplicado" /></span>
                <div className={espelho.enquadramento.aliquota_aplicada != null ? derivVal : `${derivVal} text-gray-400`}>
                  {espelho.enquadramento.aliquota_aplicada != null
                    ? fmt.pct(espelho.enquadramento.aliquota_aplicada)
                    : <span className="text-sm font-normal">não informado</span>}
                </div>
              </div>
            </div>

            {espelho.enquadramento.confirmado && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-4 mt-5 pt-4 border-t border-gray-100">
                <div>
                  <span className={derivLabel}>FAP<Fundamentacao campo="fap_aplicado" /></span>
                  <div className={derivVal}>{fmt.num(espelho.enquadramento.fap, 4)}</div>
                </div>
                <div>
                  <span className={derivLabel}>Alíquota efetiva<Fundamentacao campo="aliquota_efetiva" /></span>
                  <div className={derivVal}>{fmt.pct(espelho.enquadramento.aliquota_efetiva)}</div>
                </div>
                {/* Item 6: a divergência é o produto — é o número pelo qual o cliente paga.
                    Peso maior, posição de resultado, e cor COM rótulo em texto: positiva é
                    crédito a recuperar, negativa é passivo a regularizar. Confundir as duas num
                    laudo é grave — quem compensa crédito inexistente responde com multa. */}
                <div className="col-span-2">
                  <span className={derivLabel}>Divergência</span>
                  {espelho.enquadramento.divergencia_pp == null ? (
                    <div className={`${derivVal} text-gray-400`}>—</div>
                  ) : (
                    <div className={`flex items-baseline gap-2 ${
                      espelho.enquadramento.divergencia_pp > 0 ? "text-blue-700"
                      : espelho.enquadramento.divergencia_pp < 0 ? "text-red-700" : "text-gray-700"}`}>
                      <span className="text-2xl font-bold tabular-nums">{fmt.pp(espelho.enquadramento.divergencia_pp)}</span>
                      <span className="text-xs font-medium">
                        {espelho.enquadramento.divergencia_pp > 0 ? "pagou a mais — crédito a recuperar"
                         : espelho.enquadramento.divergencia_pp < 0 ? "pagou a menos — passivo a regularizar"
                         : "sem divergência"}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            <p className="text-[11px] text-gray-400 mt-4">
              {espelho.enquadramento.origem}
              {espelho.motivo && ` ${espelho.motivo}`}
            </p>
          </>
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

      {/* CPRB — estado explícito de verificação (RF-0.163..0.166) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-1">CPRB — desoneração da folha</h2>
        <p className="text-[11px] text-gray-400 mb-3">
          O estado precisa ser explícito: um bloco vazio não diz se a empresa <b>não optou</b> ou se
          <b> ninguém verificou</b>. Não confundir com o período de apuração.
          {/* Item 3: a citação saiu daqui. Vem da tabela versionada — quando a lei mudar,
              acrescenta-se linha na tabela e esta tela acompanha, em vez de exibir fundamento
              revogado com aparência de vigente. */}
          <Fundamentacao campo="cprb" />
        </p>

        {/* seletor dos três estados */}
        <div className="flex flex-col gap-2 mb-3">
          {([
            ["nao_informado", "Não verificado", "padrão — vai à conferência; a memória registra que a CPRB não foi verificada"],
            ["nao_optante", "Verificado: não optante", "marcação explícita (autor e data); cálculo com a patronal cheia"],
            ["optante", "Optante", "com a lista de períodos abaixo"],
          ] as [CprbStatus, string, string][]).map(([v, label, hint]) => (
            <label key={v} className={`flex items-start gap-2 rounded-lg border p-2 cursor-pointer ${cprbStatus === v ? "border-teal-400 bg-teal-50" : "border-gray-200"}`}>
              <input type="radio" name="cprb_status" className="mt-0.5" checked={cprbStatus === v} onChange={() => setCprbStatus(v)} />
              <span><b className="text-sm text-gray-800">{label}</b><br /><span className="text-[11px] text-gray-500">{hint}</span></span>
            </label>
          ))}
        </div>

        {cprbStatus === "nao_optante" && (cprbVerif.por || cprbVerif.em) && (
          <p className="text-[11px] text-gray-500 mb-2">
            Última verificação: {cprbVerif.por || "—"}{cprbVerif.em ? ` em ${new Date(cprbVerif.em).toLocaleDateString("pt-BR")}` : ""}.
          </p>
        )}

        {cprbStatus === "optante" && (
          <div className="border-t border-gray-100 pt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600">Períodos de opção (janeiro a dezembro)</span>
              <button type="button" onClick={() => setCprb((l) => [...l, { inicio: "", fim: "", fim_aberto: false }])}
                className="text-[11px] text-teal-700 hover:underline">+ período</button>
            </div>
            <p className="text-[11px] text-gray-400 mb-2">
              Coexistência com a patronal parcial a partir de 01/2025 (2025: 5% · 2026: 10% · 2027: 15%);
              RAT e Terceiros sempre devidos.
            </p>
            {cprb.length === 0 && <p className="text-xs text-gray-500">Nenhum período. Adicione ao menos um.</p>}
            {cprb.map((p, i) => {
              const err = validaCprbPeriodo(p, form.data_abertura, form.data_encerramento);
              return (
                <div key={i} className="mb-2">
                  <div className="grid grid-cols-12 gap-2 items-center">
                    <input type="month" max={CPRB_FIM_LIMITE} className={`${inputCls} col-span-4`} value={p.inicio || ""}
                      onChange={(e) => setCprb((l) => l.map((x, j) => j === i ? { ...x, inicio: e.target.value } : x))} />
                    <input type="month" max={CPRB_FIM_LIMITE} disabled={!!p.fim_aberto}
                      className={`${inputCls} col-span-4 ${p.fim_aberto ? "opacity-40" : ""}`}
                      value={p.fim_aberto ? "" : (p.fim || "")}
                      placeholder={p.fim_aberto ? "vigente" : "fim (dez.)"}
                      onChange={(e) => setCprb((l) => l.map((x, j) => j === i ? { ...x, fim: e.target.value } : x))} />
                    <label className="col-span-3 flex items-center gap-1 text-[11px] text-gray-600">
                      <input type="checkbox" checked={!!p.fim_aberto}
                        onChange={(e) => setCprb((l) => l.map((x, j) => j === i ? { ...x, fim_aberto: e.target.checked, fim: e.target.checked ? "" : x.fim } : x))} />
                      em aberto
                    </label>
                    <button type="button" className="col-span-1 text-red-400 text-sm" onClick={() => setCprb((l) => l.filter((_, j) => j !== i))}>✕</button>
                  </div>
                  {err && <p className="text-[11px] text-red-500 mt-1">{err}</p>}
                  {!err && !p.fim && !p.fim_aberto && p.inicio && (
                    <p className="text-[11px] text-amber-600 mt-1">Fim em branco: sem marcar “em aberto”, fecha em 12/{p.inicio.slice(0, 4)}.</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
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

      {msg && <p className={`text-sm mb-3 ${msg.includes("salvos") || msg.includes("zerado") ? "text-emerald-600" : "text-red-600"}`}>{msg}</p>}
      <button onClick={salvar} disabled={salvando}
        className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
        {salvando ? "Salvando…" : "Salvar dados da empresa"}
      </button>

      {/* RF-0.207: arquivar e excluir. Separados de propósito — um é status, o outro é perda
          definitiva, e eles não podem parecer a mesma coisa. */}
      <section className="mt-8 border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Arquivar ou excluir</h2>

        <div className="flex items-start gap-4 pb-4 border-b border-gray-100">
          <div className="flex-1">
            <p className="text-xs font-medium text-gray-700">Arquivar — reversível</p>
            <p className="text-[11px] text-gray-500">
              A empresa sai da lista principal e <b>todos os dados permanecem íntegros</b>:
              estabelecimentos, atividades, enquadramento apurado, regime e CPRB. Pode ser
              restaurada a qualquer momento.
            </p>
          </div>
          {arquivada ? (
            <button onClick={desarquivar} disabled={salvando}
              className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap">
              Restaurar
            </button>
          ) : (
            <button onClick={arquivar} disabled={salvando}
              className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap">
              Arquivar
            </button>
          )}
        </div>

        <div className="pt-4">
          <p className="text-xs font-medium text-red-700">Excluir — irreversível</p>
          <p className="text-[11px] text-gray-500 mb-3">
            Apaga a empresa e <b>todo o enquadramento já apurado</b>, sem possibilidade de volta.
            Exige digitar a razão social e é restrita ao titular do escritório. Se a intenção é
            só tirar da lista, use Arquivar.
          </p>
          {!mostrarExclusao ? (
            <button onClick={() => setMostrarExclusao(true)}
              className="text-xs text-red-700 hover:underline">
              Quero excluir esta empresa
            </button>
          ) : (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
              <label className="text-[11px] text-red-800">
                Para confirmar, digite a razão social exatamente como cadastrada:
                <b> {form.razao_social || "—"}</b>
              </label>
              <input className={`${inputCls} mt-2`} value={confirmaExclusao}
                onChange={(e) => setConfirmaExclusao(e.target.value)}
                placeholder="Razão social" autoComplete="off" />
              <div className="flex gap-2 mt-3">
                <button onClick={() => { setMostrarExclusao(false); setConfirmaExclusao(""); }}
                  className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800">Cancelar</button>
                <button onClick={excluir}
                  disabled={salvando || confirmaExclusao.trim().toLowerCase() !== (form.razao_social || "").trim().toLowerCase()}
                  className="bg-red-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-red-700 disabled:opacity-40">
                  Excluir definitivamente
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
