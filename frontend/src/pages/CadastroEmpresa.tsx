// ==============================================================
// SST ESOCIAL GOV — Cadastro da Empresa (Adendo 03, v1)
// O enquadramento é do ESTABELECIMENTO (matriz), não da empresa (RN-17). Esta tela guarda
// identificação, período de apuração, regime/CPRB por período e contato; o enquadramento
// aparece como espelho read-only da matriz.
// ==============================================================
import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";
import { Fundamentacao, hojeISO } from "../components/Fundamentacao";
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
// Lista fechada em vez de texto livre: "IV", "Anexo IV", "anexo 4" e "4" gravavam quatro coisas
// diferentes para a mesma realidade, e o anexo vai decidir se há RAT a apurar no período.
const ANEXOS_SIMPLES = ["I", "II", "III", "IV", "V"];
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
// Competencia por extenso: "novembro de 2021", nao "2021-11" (Carolina, 23/10). O formato
// tecnico aparece em pergunta e aviso lidos por quem nao escreveu o sistema.
const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
               "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const mesExtenso = (ym: string) => {
  const [a, m] = (ym || "").split("-");
  const i = Number(m) - 1;
  return a && MESES[i] ? `${MESES[i]} de ${a}` : (ym || "—");
};

// Quantas competencias ha entre dois meses, inclusive. Usado para dizer o tamanho do estrago
// antes de apagar um periodo de regime — "60 competencias" pesa diferente de "a janela".
const competenciasEntre = (de: string, ate: string) => {
  if (!de || !ate) return 0;
  const [a1, m1] = de.split("-").map(Number);
  const [a2, m2] = ate.split("-").map(Number);
  return Math.max(0, (a2 - a1) * 12 + (m2 - m1) + 1);
};

const ymToDate = (s: string) => (s ? `${s}-01` : null);
const dateToYm = (iso: string | null) => (iso ? iso.slice(0, 7) : "");
const mesesEntre = (a: string, b: string) => {
  if (!a || !b) return 0;
  const [ya, ma] = a.split("-").map(Number), [yb, mb] = b.split("-").map(Number);
  return (yb - ya) * 12 + (mb - ma);
};

// Periodo de REGIME tributario. Servia tambem a CPRB ate 26/10, quando ela passou a se declarar
// por ANO (ver AnoCprb) — e 'fim_aberto' saiu junto, porque opcao em aberto nao existe na CPRB.
interface Periodo { regime?: string; anexo_simples?: string; inicio: string; fim: string;
  declarado_por?: string | null; declarado_em?: string | null; }
type CprbStatus = "nao_informado" | "nao_optante" | "optante";

// Nomes legíveis dos campos rastreados, para a dica de procedência não mostrar nome de coluna.
const ROTULO_CAMPO: Record<string, string> = {
  razao_social: "razão social", nome_fantasia: "nome fantasia", cnae_principal: "CNAE principal",
  data_abertura: "data de abertura", data_encerramento: "data de encerramento",
  tipo_logradouro: "tipo do logradouro",
  endereco: "logradouro", numero: "número", complemento: "complemento", bairro: "bairro",
  cidade: "cidade", uf: "UF", cep: "CEP",
};
const rotuloCampo = (c: string) => ROTULO_CAMPO[c] || c;

// Tipos de logradouro para escolha quando a consulta NAO devolver o dado (Carolina, 23/10).
// Texto livre produz "RUA", "Rua", "R." e "rua" na mesma coluna, e o endereco entra em peca
// protocolada. A lista nao e fechada: o valor que vier da consulta entra como opcao mesmo fora
// dela — no registro do Banco do Brasil o tipo e QUADRA, e perder isso seria pior que a variacao.
const TIPOS_LOGRADOURO = ["RUA", "AVENIDA", "TRAVESSA", "RODOVIA", "ESTRADA", "PRAÇA",
                          "ALAMEDA", "QUADRA", "VIA", "LARGO"];

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

// A ausência é ESTRUTURADA, não narrada. A linha fica onde está e o valor dá lugar a um
// marcador, em vez de sumir e virar frase embaixo do bloco. Duas razões: as colunas devido e
// aplicado continuam paralelas linha a linha, que é o que deixa o olho comparar; e a lacuna
// aparece no lugar exato onde o dado vai entrar quando a captura do RAT base e do FAP chegar
// pela tela Estabelecimentos — aí o desenho não muda, só os valores aparecem.
const NaoInformado = () => (
  <span className="inline-block rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">
    não informado
  </span>
);

// Qual parte do desdobramento falta, para a frase dizer exatamente essa e não uma genérica.
// Devolve null quando os dois estão informados — e aí não há nada a explicar.
function faltaDesdobramento(rat: number | null | undefined, fap: number | null | undefined) {
  if (rat == null && fap == null) return "o RAT base e o FAP não forem informados";
  if (rat == null) return "o RAT base não for informado";
  if (fap == null) return "o FAP não for informado";
  return null;
}

// AS DUAS LEITURAS DO MESMO NÚMERO APLICADO (Carolina, 24/10).
//
// Quando a empresa informou só um percentual, sem dizer se é a alíquota BASE ou a EFETIVA, o
// mesmo valor produz achados opostos. O caso real: grau 3, RAT base 3,00%, FAP publicado 0,5000,
// devida 1,50%. Lido como efetiva, dá +1,50 p.p. de crédito; lido como base, 3,00 × 0,5000 =
// 1,50% e a divergência é zero. E escrever a base no lugar da efetiva é o erro mais provável
// justamente porque o número coincide com o grau.
//
// A tela deixa de escolher: mostra as duas e não afirma nenhuma. O cálculo "como base" usa o FAP
// PUBLICADO, e isso é hipótese — o FAP que a empresa aplicou é desconhecido, é o dado que falta.
// Por isso o resultado aparece rotulado como leitura, nunca como divergência apurada.
function leiturasDoAplicado(
  aplicada: number | null | undefined,
  fapPublicado: number | null | undefined,
  efetivaDevida: number | null | undefined,
) {
  if (aplicada == null || efetivaDevida == null) return null;
  const r4 = (n: number) => Number(n.toFixed(4));
  return {
    comoEfetiva: r4(aplicada - efetivaDevida),
    efetivaSeBase: fapPublicado == null ? null : r4(aplicada * fapPublicado),
    comoBase: fapPublicado == null ? null : r4(aplicada * fapPublicado - efetivaDevida),
  };
}

// Situação da competência no espelho (espelha api/services/enquadramento_situacao.py)
// Concordam com ROTULO do backend, no feminino, porque entram na frase "Esta competência
// está ___". "apurado (falta o aplicado)" era o rótulo anterior a 19/10 e dizia o contrário do
// que o estado significa hoje: apurada é a que o motor fechou, tenha o aplicado ou não.
const ESP_SIT: Record<string, string> = {
  conferencia: "em conferência", apurado: "apurada", conferido: "conferida",
  nao_auditada: "não auditada quanto ao RAT",
};

// A CPRB SE DECLARA POR ANO, NÃO POR PERÍODO (Carolina, 26/10, pontos 4, 5 e 6).
//
// A tela pedia mês de início e mês de fim, e oferecia "em aberto". Nenhuma das três coisas existe
// na CPRB: pelo art. 9º, §13, da Lei 12.546/2011 a opção se manifesta no pagamento da contribuição
// de JANEIRO e é irretratável para todo o ano-calendário. Cada ano exige um ato novo — propagar
// uma opção "em aberto" faria o sistema afirmar opção em anos que a empresa nunca manifestou, e
// essa afirmação vai para a memória de cálculo.
//
// A única exceção é o primeiro ano com receita apurada: empresa que inicia atividade no curso do
// ano opta a partir daquele mês. Por isso o ano carrega um mês, e só nesse caso.
type AnoCprb = { ano: number | null; parcial: boolean; mesInicio: string };

const MESES_NUM = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"];

// Converte o que o backend guarda (par de datas) no que a tela declara (ano).
const periodosParaAnos = (periodos: any[]): AnoCprb[] =>
  (periodos || []).map((p: any) => {
    const ini = String(p.inicio || "");
    const mes = ini.slice(5, 7) || "01";
    return { ano: Number(ini.slice(0, 4)) || null, parcial: mes !== "01", mesInicio: mes };
  }).filter((a) => a.ano);

// E de volta: janeiro a dezembro do ano, salvo o primeiro ano com receita apurada.
const anosParaPeriodos = (anos: AnoCprb[]) =>
  anos.filter((a) => a.ano).map((a) => ({
    inicio: `${a.ano}-${a.parcial ? a.mesInicio : "01"}-01`,
    fim: `${a.ano}-12-01`,
    fim_confirmado: false,     // não existe opção em aberto: o ano sempre fecha em dezembro
  }));

// Validação ao SALVAR, não ao nascer. A linha nova vinha com "Informe o início do período de
// CPRB" em vermelho antes de a pessoa digitar qualquer coisa — erro antes do erro ensina a
// ignorar o vermelho, e aí o aviso que importa passa despercebido.
const validaAnosCprb = (anos: AnoCprb[]): string => {
  if (anos.length === 0) return "Optante pela CPRB: informe ao menos um ano de opção.";
  const vistos = new Set<number>();
  for (const a of anos) {
    if (!a.ano) return "Escolha o ano de cada opção.";
    if (vistos.has(a.ano)) return `O ano ${a.ano} aparece duas vezes. Cada ano-calendário é uma opção só.`;
    vistos.add(a.ano);
    if (a.parcial && !a.mesInicio) return `Em ${a.ano}, informe o mês em que a opção começa.`;
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
  // SOBREPOSIÇÃO. A cobertura mês a mês abaixo acha lacuna, não excesso: duas linhas cobrindo a
  // mesma competência passavam, e nenhuma regra dizia qual prevalece — a leitura do regime fica
  // ambígua justamente onde ela decide se há RAT a apurar. Comparado par a par: a lista tem
  // poucas linhas, e ordenar para varrer custaria mais do que compara.
  const comDatas = regimes.filter((r) => r.regime && r.inicio);
  for (let a = 0; a < comDatas.length; a++) {
    for (let b = a + 1; b < comDatas.length; b++) {
      const x = comDatas[a], y = comDatas[b];
      const xFim = x.fim || "9999-12", yFim = y.fim || "9999-12";
      if (x.inicio <= yFim && y.inicio <= xFim) {
        return `Dois períodos de regime se sobrepõem (${mesExtenso(x.inicio)} e ${mesExtenso(y.inicio)}). Cada competência precisa de um regime só.`;
      }
    }
  }
  const validos = regimes.filter((r) => r.regime && r.inicio);
  if (validos.length === 0) return `Declare o regime tributário para o período de apuração (${mesExtenso(pIni)} a ${mesExtenso(pFim)}).`;
  // varre mês a mês a janela de apuração procurando o primeiro mês descoberto
  let m = pIni;
  while (m <= pFim) {
    const coberto = validos.some((r) => r.inicio <= m && (!r.fim || r.fim >= m));
    if (!coberto) return `Lacuna de regime em ${mesExtenso(m)}: todo o período de apuração precisa estar coberto.`;
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
    tipo_logradouro: "", endereco: "", numero: "", complemento: "", bairro: "", cidade: "", uf: "", cep: "",
    contato_nome: "", contato_email: "", contato_telefone: "",
  });
  // Indice do periodo de regime aguardando confirmacao de remocao, ou null.
  const [removerRegime, setRemoverRegime] = useState<number | null>(null);
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
  const [cprb, setCprb] = useState<AnoCprb[]>([]);
  const [cprbStatus, setCprbStatus] = useState<CprbStatus>("nao_informado");
  const [cprbVerif, setCprbVerif] = useState<{ por?: string; em?: string }>({});
  // A transição vem do backend: as proporções de cada ano e a ressalva do décimo terceiro são
  // regra de lei, e viajam de lá para que esta tela e a memória de cálculo digam a mesma coisa.
  const [cprbRegras, setCprbRegras] = useState<any[]>([]);
  const [cprbAvisos, setCprbAvisos] = useState<{ decimo?: string; anoCalendario?: string }>({});
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
        tipo_logradouro: d.tipo_logradouro ?? "",
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
      // declarado_por/declarado_em vem JUNTO: sem eles o rodape de autoria nunca teria o que
      // mostrar, porque o backend devolve e este map descartaria em silencio.
      (r.data || []).map((p: any) => ({ regime: p.regime, anexo_simples: p.anexo_simples,
        inicio: dateToYm(p.inicio), fim: dateToYm(p.fim),
        declarado_por: p.declarado_por ?? null, declarado_em: p.declarado_em ?? null }))
    )).catch(() => {});
    apiClient.get(`/empresas/${empresaId}/cprb`).then((r) => {
      const d = r.data || {};
      setCprbStatus((d.status as CprbStatus) || "nao_informado");
      setCprb(periodosParaAnos(d.periodos));
      setCprbRegras((d.transicao || []).filter((r: any) => r.existe));
      setCprbAvisos({ decimo: d.aviso_decimo_terceiro, anoCalendario: d.aviso_ano_calendario });
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
        tipo_logradouro: ou(x.tipo_logradouro, f.tipo_logradouro),
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
        tipo_logradouro: x.tipo_logradouro ?? null,
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
      // SÓ PREENCHE CAMPO VAZIO. Antes esta busca sobrescrevia logradouro, bairro, cidade e UF
      // com o que o ViaCEP devolvesse, e isso falseava a procedência: numa empresa consultada na
      // Receita, a âncora gravada é o valor da Receita; o ViaCEP trocava o valor por outro — às
      // vezes só na grafia, "ALMIRANTE TAMANDARE" contra "Rua Almirante Tamandaré" — e, ao
      // salvar, o backend via valor diferente da âncora e marcava o campo como ALTERADO À MÃO.
      // Ninguém havia alterado nada: achado falso dentro do mecanismo que existe para impedir
      // achado falso. São ainda fontes que discordam na estrutura, porque o ViaCEP devolve o
      // tipo embutido no logradouro e a Receita devolve os dois separados.
      //
      // Preenchendo só o vazio, a busca segue útil no cadastro manual e nunca contradiz a
      // Receita. O que ela preencher, o usuário revisa e salva, e aí vale como declarado — o
      // rótulo honesto, porque não veio do cadastro oficial.
      const vazio = (v: any) => !String(v ?? "").trim();
      const sugestao: Record<string, string | undefined> = {
        endereco: data.logradouro, bairro: data.bairro, cidade: data.localidade, uf: data.uf,
      };
      const preencher: Record<string, string> = {};
      let mantidos = 0;
      for (const [campo, valor] of Object.entries(sugestao)) {
        if (!valor) continue;
        if (vazio(form[campo])) preencher[campo] = valor;
        else if (String(form[campo]).trim().toUpperCase() !== valor.trim().toUpperCase()) mantidos += 1;
      }
      if (Object.keys(preencher).length) setForm((f: any) => ({ ...f, ...preencher }));
      setCepMsg(mantidos ? "CEP encontrado. Os campos já preenchidos foram mantidos." : "");
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
      const errCprb = validaAnosCprb(cprb);
      if (errCprb) { setMsg(`CPRB — ${errCprb}`); return; }
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
        // tipo_logradouro ESTAVA FALTANDO AQUI ate 23/10. A coluna existe desde a migration 044,
        // o backend aceita e a tela mostra o campo — mas o corpo do PUT nao o enviava, entao a
        // consulta preenchia a tela e o salvamento descartava. O campo ficava eternamente vazio
        // no banco sem nenhum erro, e o endereco saia sem o tipo nos documentos.
        tipo_logradouro: form.tipo_logradouro || null,
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
        periodos: cprbStatus === "optante" ? anosParaPeriodos(cprb) : [],
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
            {/* "CNPJ da matriz", não "raiz" (Carolina, 23/10). O campo guarda os 14 dígitos:
                empresas.cnpj é String(14), único e obrigatório, e consultar_cnpj recusa o que
                não tiver 14. Raiz são os oito primeiros, e ela nunca é armazenada — é derivada
                por fatiamento onde alguém precisa dela (a memória faz cnpj[:8] para imprimir
                "CNPJ raiz", e ali está certo). O rótulo é que dizia uma coisa e o campo guardava
                outra, bem no campo que ancora a empresa e por onde as filiais se agrupam. */}
            <label className={labelCls}>CNPJ da matriz</label>
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
                {/* A contagem de "preenchido à mão" SAIU daqui (Carolina, 23/10) e foi para o
                    rodapé do bloco. Esta linha fala da CONSULTA — quando foi feita e o que dela
                    foi editado depois. Quantos campos nunca vieram da consulta é fato do
                    registro inteiro; ancorado logo abaixo de "Consultado em…", parecia dizer
                    que um dos campos trazidos pela consulta tinha sido digitado. */}
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
        {/* RODAPÉ DO BLOCO: composição do registro, não da consulta. Fica aqui, depois de todos
            os campos, porque é sobre o conjunto deles — e não embaixo do CNPJ, onde era lido
            como se um campo da consulta tivesse sido digitado. O campo preenchido à mão se
            identifica sozinho, pela marcação (declarado) e pelo fundo azul. */}
        {resumoOrigem?.campos_declarados?.length > 0 && (
          <p className="text-[11px] text-gray-400 mt-3 pt-2 border-t border-gray-100">
            {resumoOrigem.campos_declarados.length} campo
            {resumoOrigem.campos_declarados.length > 1 ? "s preenchidos" : " preenchido"} à mão:{" "}
            <span className="text-gray-600">
              {resumoOrigem.campos_declarados.map(rotuloCampo).join(", ")}
            </span>.
          </p>
        )}
      </section>

      {/* Endereço (matriz) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-3">Endereço (matriz)</h2>
        {/* Os sete campos deste bloco vinham da consulta e nenhum dizia isso. A maquinaria de
            procedência já os rastreava no backend — o bloco é que nunca a chamava. Importa
            porque o endereço é editável: a Receita pode estar desatualizada e o cliente
            corrigir, e o laudo precisa saber se descreve o estabelecimento conforme o cadastro
            oficial ou conforme alguém digitou. */}
        <div className="grid grid-cols-6 gap-4">
          <div className="col-span-2">
            <label className={labelCls}>CEP<Procedencia mapa={camposOrigem} campo="cep" genero="o" /></label>
            <input className={fundoProcedencia(camposOrigem, "cep", inputCls)} value={form.cep}
              onChange={(e) => { const v = maskCep(e.target.value); set("cep", v); if (v.replace(/\D/g, "").length === 8) buscarCep(v); }}
              onBlur={(e) => buscarCep(e.target.value)} maxLength={9} placeholder="00000-000" inputMode="numeric" />
            {cepMsg && <p className="text-[11px] text-amber-600 mt-1">{cepMsg}</p>}
          </div>
          {/* Campo PRÓPRIO, não prefixo concatenado no logradouro: a fonte separa os dois, e o
              tipo nem sempre abre o logradouro. Assim o laudo compõe o endereço na ordem que
              quiser e a busca por logradouro não precisa limpar prefixo. */}
          <div className="col-span-1">
            <label className={labelCls}>Tipo<Procedencia mapa={camposOrigem} campo="tipo_logradouro" genero="o" /></label>
            {/* Escolha, nao digitacao. Sem valor, a opcao em branco fica selecionada e o campo
                diz "— escolher —": o que nao pode e ficar mudo, porque o tipo entra no endereco
                que vai impresso em peca protocolada. O valor vindo da consulta entra na lista
                mesmo quando nao e um dos comuns. */}
            <select className={fundoProcedencia(camposOrigem, "tipo_logradouro", inputCls)}
              value={form.tipo_logradouro}
              onChange={(e) => set("tipo_logradouro", e.target.value)}>
              <option value="">— escolher —</option>
              {(TIPOS_LOGRADOURO.includes(form.tipo_logradouro)
                ? TIPOS_LOGRADOURO
                : [form.tipo_logradouro, ...TIPOS_LOGRADOURO].filter(Boolean)
               ).map((tp) => <option key={tp} value={tp}>{tp}</option>)}
            </select>
          </div>
          <div className="col-span-3">
            <label className={labelCls}>Logradouro<Procedencia mapa={camposOrigem} campo="endereco" genero="o" /></label>
            <input className={fundoProcedencia(camposOrigem, "endereco", inputCls)} value={form.endereco}
              onChange={(e) => set("endereco", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Número<Procedencia mapa={camposOrigem} campo="numero" genero="o" /></label>
            <input className={fundoProcedencia(camposOrigem, "numero", inputCls)} value={form.numero}
              onChange={(e) => set("numero", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Complemento<Procedencia mapa={camposOrigem} campo="complemento" genero="o" /></label>
            <input className={fundoProcedencia(camposOrigem, "complemento", inputCls)} value={form.complemento}
              onChange={(e) => set("complemento", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Bairro<Procedencia mapa={camposOrigem} campo="bairro" genero="o" /></label>
            <input className={fundoProcedencia(camposOrigem, "bairro", inputCls)} value={form.bairro}
              onChange={(e) => set("bairro", e.target.value)} />
          </div>
          <div className="col-span-4">
            <label className={labelCls}>Cidade<Procedencia mapa={camposOrigem} campo="cidade" /></label>
            <input className={fundoProcedencia(camposOrigem, "cidade", inputCls)} value={form.cidade}
              onChange={(e) => set("cidade", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>UF<Procedencia mapa={camposOrigem} campo="uf" /></label>
            <select className={fundoProcedencia(camposOrigem, "uf", inputCls)} value={form.uf}
              onChange={(e) => set("uf", e.target.value)}>
              <option value="">—</option>{UFS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>
      </section>

      {/* ORDEM DOS BLOCOS — DEFINIDA, NÃO ACIDENTAL (Tales, 23/10):
          identificação · endereço · regime tributário · enquadramento · CPRB · contato.
          Quem reordenar precisa saber o que quebra: o regime vem ANTES do enquadramento
          porque é ele que decide se existe alguma coisa a calcular — no Simples fora do
          Anexo IV não há RAT a apurar. Com o regime abaixo do resultado, quem preenche de
          cima para baixo lê a divergência antes de declarar o regime que a anula. */}
      {/* Regime tributário por período (RF-0.156) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-gray-800">Regime tributário (por período)</h2>
          <button type="button" onClick={() => setRegimes((l) => [...l, { regime: "", inicio: form.periodo_inicio, fim: "" }])}
            className="text-[11px] text-teal-700 hover:underline">+ período</button>
        </div>
        {regimes.length === 0 && <p className="text-xs text-gray-500">Nenhum período. A empresa pode mudar de regime dentro da janela.</p>}
        {/* A linha tinha quatro campos e nenhum rótulo: "De" e "Até" só se distinguiam pela
            ordem em que aparecem. Os nomes vêm uma vez, no alto, e não se repetem por linha. */}
        {/* Colunas PROPORCIONAIS, não as 12 fixas (Carolina, 24/10). Com col-span de 12 o campo
            do anexo cabia em 2 e cortava "— não se aplica" em "— não se apli"; e não dava para
            roubar coluna de "De"/"Até", que precisam de largura para o ano do mês aparecer.
            Em frações, o botão do × ocupa só o necessário e devolve o espaço. */}
        {regimes.length > 0 && (
          <div className="grid grid-cols-[1.1fr_1.1fr_1fr_1fr_auto] gap-2 mb-1">
            <span className={labelCls}>Regime</span>
            <span className={labelCls}>Anexo do Simples</span>
            <span className={labelCls}>De</span>
            <span className={labelCls}>Até</span>
            <span />
          </div>
        )}
        {regimes.map((p, i) => (
          <div key={i} className="grid grid-cols-[1.1fr_1.1fr_1fr_1fr_auto] gap-2 mb-2 items-center">
            <select className={inputCls} value={p.regime || ""} onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, regime: e.target.value } : x))}>
              <option value="">Regime…</option>{REGIMES.map((r) => <option key={r.v} value={r.v}>{r.label}</option>)}
            </select>
            {/* Lista fechada no lugar de texto livre. Fora do Simples o campo fica desabilitado e
                legendado, em vez de um vão em branco: espaço vazio não diz se o campo não existe
                ali ou se ninguém preencheu. */}
            {p.regime === "simples" ? (
              <select className={inputCls} value={p.anexo_simples || ""}
                onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, anexo_simples: e.target.value } : x))}>
                <option value="">Anexo…</option>
                {ANEXOS_SIMPLES.map((a) => <option key={a} value={a}>Anexo {a}</option>)}
                {/* Valor gravado antes da lista fechada: entra como opção para não sumir calado
                    da tela nem do registro quando alguém abrir e salvar. */}
                {p.anexo_simples && !ANEXOS_SIMPLES.includes(p.anexo_simples) && (
                  <option value={p.anexo_simples}>{p.anexo_simples} — valor antigo</option>
                )}
              </select>
            ) : (
              <select className={`${inputCls} text-gray-400`} value="" disabled>
                <option>— não se aplica</option>
              </select>
            )}
            {/* Três colunas, não duas: em duas o campo de mês cortava o ano, e é ele que delimita
                a base de cálculo — não dá para ler onde o período começa. */}
            <input type="month" className={inputCls} value={p.inicio || ""} onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, inicio: e.target.value } : x))} />
            <input type="month" className={inputCls} value={p.fim || ""} onChange={(e) => setRegimes((l) => l.map((x, j) => j === i ? { ...x, fim: e.target.value } : x))} />
            {/* O × PERGUNTA antes de apagar (Carolina, 23/10). Um clique removia a linha calado,
                e o regime e premissa de calculo de todas as competencias da janela: clique
                acidental derrubava a base da apuracao inteira, e quem nao viu o clique nao
                saberia por que os numeros mudaram. */}
            <button type="button" className="text-red-400 text-sm px-1"
              title="Remover este período" onClick={() => setRemoverRegime(i)}>✕</button>
          </div>
        ))}
        {regimes.length > 0 && (
          <p className="text-[11px] text-gray-500 mt-1">“Até” vazio significa período em aberto.</p>
        )}

        {/* CONFIRMAÇÃO DE REMOÇÃO — nomeia a linha, não é um "tem certeza?" genérico.
            Quem clicou precisa reconhecer o que está prestes a sumir; e o aviso diz a
            consequência real, que é a revogação das conferências apoiadas naquele regime. */}
        {removerRegime !== null && regimes[removerRegime] && (() => {
          const p = regimes[removerRegime];
          const nome = REGIMES.find((r) => r.v === p.regime)?.label || "Regime não informado";
          const anexo = p.regime === "simples" && p.anexo_simples ? `, Anexo ${p.anexo_simples}` : "";
          const ate = p.fim || form.periodo_fim;
          const n = competenciasEntre(p.inicio, ate);
          return (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                 onClick={() => setRemoverRegime(null)}>
              <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl"
                   onClick={(e) => e.stopPropagation()}>
                <h3 className="text-base font-bold text-gray-900">Remover este período de regime?</h3>
                <p className="text-sm text-gray-700 mt-2">
                  <b>{nome}</b>{anexo}, de <b>{mesExtenso(p.inicio)}</b>
                  {p.fim ? <> a <b>{mesExtenso(p.fim)}</b></> : <> em diante</>}.
                </p>
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] text-amber-900">
                  O regime é premissa de cálculo{n > 0 ? <> d{n === 1 ? "a" : "as"} <b>{n} competência{n > 1 ? "s" : ""}</b> da janela</> : " das competências da janela"}.
                  Removendo-o, as conferências que se apoiavam nele são revogadas e precisam ser refeitas.
                </div>
                <div className="flex gap-2 mt-5">
                  <button type="button" onClick={() => setRemoverRegime(null)}
                    className="px-4 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
                    Cancelar
                  </button>
                  <button type="button"
                    onClick={() => { setRegimes((l) => l.filter((_, j) => j !== removerRegime)); setRemoverRegime(null); }}
                    className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700">
                    Remover o período
                  </button>
                </div>
              </div>
            </div>
          );
        })()}

        {/* RODAPÉ: quem declarou. Regime, anexo e as duas datas são dado DECLARADO — ninguém
            consulta isso em lugar nenhum. A memória de cálculo se apoia nessa afirmação para
            dizer que há ou não RAT a apurar; questionada a premissa, precisa haver a quem
            atribuí-la. Mostra a declaração mais recente; sem autoria registrada, não afirma. */}
        {(() => {
          // Predicado de tipo, nao `as`: o filtro ja garante que os dois campos existem, e isto
          // informa isso ao compilador. Com `r: any` o reduce devolvia Periodo de novo e o
          // new Date() recebia string|null|undefined.
          type ComAutor = Periodo & { declarado_por: string; declarado_em: string };
          const comAutor = regimes.filter(
            (r): r is ComAutor => !!r.declarado_por && !!r.declarado_em
          );
          if (!comAutor.length) return null;
          const ult = comAutor.reduce((a, b) => (a.declarado_em > b.declarado_em ? a : b));
          const d = new Date(ult.declarado_em);
          return (
            <p className="text-[11px] text-gray-400 mt-3 pt-2 border-t border-gray-100">
              Declarado por <span className="text-gray-600">{ult.declarado_por}</span> em{" "}
              {d.toLocaleDateString("pt-BR")} às {d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}.
            </p>
          );
        })()}
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
            {/* O link vai para a linha de baixo de propósito. Em flex com justify-between ele
                quebrava sozinho quando a frase crescia, e quebra não intencional parece defeito. */}
            <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 mb-4">
              <p className="text-xs text-gray-700">
                {espelho.enquadramento.competencia ? (
                  <>
                    Competência <b>{fmt.competencia(espelho.enquadramento.competencia)}</b>
                    {espelho.serie_resumo?.total ? <>, de {espelho.serie_resumo.total} analisadas</> : null}
                    {/* Os QUATRO estados somam o total, e nenhum recorte entra nessa conta.
                        "sem o RAT aplicado" saiu daqui (Carolina, 24/10): ele era recorte das
                        APURADAS, e essa combinação deixou de existir — competência sem o aplicado
                        desdobrado não é apurada, porque a comparação não fecha. Quem lia "58
                        apuradas" lia 58 competências prontas para virar pedido de restituição, e
                        57 delas não tinham a informação que sustenta o pedido.
                        O recorte continua útil para operar e vive no title: dentro da fila, quais
                        esperam a empresa informar o que recolheu.
                        As vírgulas ficam coladas ao texto anterior de propósito: quebrar a linha
                        antes delas fazia o JSX inserir um espaço e sair "aplicado , 2". */}
                    {espelho.serie_resumo ? (
                      <> — <b title={espelho.serie_resumo.aguardando_aplicado > 0
                            ? `${espelho.serie_resumo.aguardando_aplicado} em conferência aguardam o RAT base e o FAP aplicados`
                            : undefined}>
                        {espelho.serie_resumo.apuradas} apurada{espelho.serie_resumo.apuradas === 1 ? "" : "s"}
                        {`, ${espelho.serie_resumo.em_conferencia} em conferência`}
                      </b>{`, ${espelho.serie_resumo.conferidas} conferida${espelho.serie_resumo.conferidas === 1 ? "" : "s"}`}
                        {espelho.serie_resumo.nao_auditadas > 0 && (
                          <>{`, `}<b>{`${espelho.serie_resumo.nao_auditadas} não auditada${espelho.serie_resumo.nao_auditadas === 1 ? "" : "s"} quanto ao RAT`}</b></>
                        )}</>
                    ) : null}
                  </>
                ) : (
                  <>Prévia — a série mensal ainda não foi apurada.</>
                )}
              </p>
              <a href="/estabelecimentos" className="text-xs text-teal-700 hover:underline inline-block mt-0.5">
                Ver enquadramento completo →
              </a>
            </div>

            {/* Item 5: dado derivado é VALOR, não caixa de entrada. Sem moldura de input, para
                ninguém tentar corrigir à mão o número que o sistema existe para calcular. */}
            {/* A premissa vem antes dos números: CNAE e grau respondem POR QUE a alíquota é
                aquela; as três caixas abaixo respondem QUANTO. Misturados na mesma régua de
                quatro colunas, o devido e o aplicado ficavam lado a lado sem dizer que são
                afirmações de autores diferentes — a lei e a empresa. */}
            {/* REGIME AFASTOU A APURAÇÃO. Não é divergência zero nem pendência: não há alíquota
                devida a comparar com a aplicada. Desenhar as três caixas aqui mostraria colunas
                vazias e um "—" na divergência, que o olho lê como "ainda não calculado" — e o
                que houve foi o contrário: está resolvido, e a resposta é que não há o que
                apurar. Por isso o bloco inteiro dá lugar ao aviso. */}
            {espelho.enquadramento.rat_aplicavel === false ? (
              <>
              {/* O REGIME ABRE A FRASE (Carolina, 24/10). Ele não é nota de rodapé do aviso: é a
                  razão de não haver o que apurar, e quem lê precisa ver o fato e a fonte na mesma
                  linha. O § ao lado vem da tabela versionada, resolvido pela data da competência,
                  como todas as outras citações. */}
              <div className="rounded-lg bg-amber-50 border border-amber-300 px-4 py-3">
                <p className="text-sm font-semibold text-amber-900">
                  {espelho.enquadramento.regime_competencia === "simples" ? "Simples Nacional" : null}
                  {espelho.enquadramento.regime_competencia === "simples" && espelho.enquadramento.anexo_competencia
                    ? `, Anexo ${espelho.enquadramento.anexo_competencia}` : null}
                  {espelho.enquadramento.regime_competencia === "simples" ? " — " : null}
                  não há RAT nem contribuições a Terceiros a apurar neste período.
                  <Fundamentacao campo="regime_tributario" em={espelho.enquadramento.competencia || hojeISO()} />
                </p>
                {espelho.enquadramento.motivo_inaplicavel && (
                  <p className="text-xs text-amber-900 mt-1 leading-snug">{espelho.enquadramento.motivo_inaplicavel}</p>
                )}
                {/* Quantas competências isso alcança. Sem o número, "não há o que apurar" parece
                    valer só para o mês exibido — e o que está em jogo é a série inteira sair do
                    universo auditado. */}
                {espelho.serie_resumo?.nao_auditadas > 0 && (
                  <p className="text-xs text-amber-900 mt-1 leading-snug">
                    {espelho.serie_resumo.nao_auditadas === 1
                      ? "1 competência não entra no universo auditado."
                      : `As ${espelho.serie_resumo.nao_auditadas} competências não entram no universo auditado.`}
                  </p>
                )}
                {espelho.enquadramento.regime_competencia && (
                  <p className="text-[11px] text-gray-600 mt-2">
                    Regime na competência: <b>
                      {espelho.enquadramento.regime_competencia === "simples" ? "Simples Nacional"
                        : espelho.enquadramento.regime_competencia === "lucro_real" ? "Lucro Real"
                        : espelho.enquadramento.regime_competencia === "lucro_presumido" ? "Lucro Presumido"
                        : espelho.enquadramento.regime_competencia}
                      {espelho.enquadramento.anexo_competencia && `, Anexo ${espelho.enquadramento.anexo_competencia}`}
                    </b>
                    {" "}— conforme declarado no cadastro da empresa.
                  </p>
                )}
              </div>

              {/* O CNAE DO CADASTRO, CHAMADO PELO NOME (Carolina, 24/10). Sem apuração de RAT não
                  existe preponderante apurada: ela se apura pelo número de segurados empregados e
                  trabalhadores avulsos em cada estabelecimento, não pelo CNAE do cartão CNPJ. A
                  tela exibia o principal do cadastro sob o título "atividade preponderante da
                  competência" — na mesma empresa, o principal é 4712-1/00 e a preponderante
                  apurada é 4120-4/00. "Um rótulo que chama um de outro, dentro da tela que
                  fundamenta a peça, ensina o erro que a peça combate."
                  Grau de risco e quadros de cálculo não aparecem aqui de propósito: não há
                  alíquota devida para comparar com nada. */}
              {espelho.enquadramento.cnae_principal_cadastro && (
                <div className="mt-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-1">
                    CNAE principal do cadastro — ainda não há preponderante apurada
                  </p>
                  <div className={`${derivVal} font-mono`}>{fmt.cnae(espelho.enquadramento.cnae_principal_cadastro)}</div>
                  {espelho.enquadramento.cnae_principal_descricao && (
                    <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">
                      {espelho.enquadramento.cnae_principal_descricao}
                    </p>
                  )}
                  <p className="text-[11px] text-gray-400 mt-2 leading-snug">
                    Sem apuração de RAT, não se exibe grau de risco nem quadros de cálculo: não há
                    alíquota devida para comparar.
                  </p>
                </div>
              )}
              </>
            ) : (
            <>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-2">
              Atividade preponderante da competência
            </p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4">
              <div>
                <span className={derivLabel}>CNAE<Fundamentacao campo="atividade_preponderante" em={espelho.enquadramento.competencia || hojeISO()} /></span>
                <div className={`${derivVal} font-mono`}>{fmt.cnae(espelho.enquadramento.cnae)}</div>
                {espelho.enquadramento.cnae_descricao && (
                  <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">{espelho.enquadramento.cnae_descricao}</p>
                )}
              </div>
              <div>
                <span className={derivLabel}>Grau de risco<Fundamentacao campo="rat_devido" em={espelho.enquadramento.competencia || hojeISO()} /></span>
                <div className={derivVal}>
                  {espelho.enquadramento.grau_risco
                    ? <>{espelho.enquadramento.grau_risco}<span className="text-sm font-normal text-gray-500"> — {espelho.enquadramento.grau_label}</span></>
                    : "—"}
                </div>
              </div>
            </div>

            {espelho.enquadramento.confirmado && (
              <div className="grid md:grid-cols-3 gap-3 mt-5 pt-4 border-t border-gray-100">
                {/* DEVIDO: cada linha decorre de norma e carrega o seu §. É a conta que a lei
                    manda fazer — RAT do Anexo I multiplicado pelo FAP publicado. */}
                <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-2">Devido pela lei</p>
                  {/* Mesma altura de linha da coluna ao lado: é o paralelismo que deixa comparar
                      linha a linha, e o marcador de ausência é mais alto que um número solto. */}
                  <div className="flex items-baseline justify-between gap-2 min-h-[1.75rem]">
                    <span className="text-[11px] text-gray-600">RAT<Fundamentacao campo="rat_devido" em={espelho.enquadramento.competencia || hojeISO()} /></span>
                    <span className="text-sm font-semibold text-gray-900 tabular-nums">{fmt.pct(espelho.enquadramento.aliquota_rat)}</span>
                  </div>
                  <div className="flex items-baseline justify-between gap-2 min-h-[1.75rem]">
                    <span className="text-[11px] text-gray-600">× FAP publicado<Fundamentacao campo="fap_publicado" em={espelho.enquadramento.competencia || hojeISO()} /></span>
                    <span className="text-sm font-semibold text-gray-900 tabular-nums">
                      {espelho.enquadramento.fap != null ? fmt.num(espelho.enquadramento.fap, 4) : "—"}
                    </span>
                  </div>
                  <div className="mt-2 pt-2 border-t border-gray-200">
                    <span className={derivLabel}>Alíquota efetiva devida<Fundamentacao campo="aliquota_efetiva" em={espelho.enquadramento.competencia || hojeISO()} /></span>
                    <div className={derivVal}>{fmt.pct(espelho.enquadramento.aliquota_efetiva)}</div>
                  </div>
                </div>

                {/* APLICADO: nenhum § aqui. Este bloco não é o que a norma manda — é o que a
                    empresa declarou no S-1005, certo ou errado. Marcar com § faria a tela
                    afirmar que a alíquota errada tem fundamento legal. O marcador correto é a
                    procedência, no rodapé da caixa. */}
                <div className="rounded-lg bg-white border-2 border-amber-300 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-2">Aplicado pela empresa</p>
                  {espelho.enquadramento.aliquota_aplicada == null ? (
                    <p className="text-sm text-gray-400 mt-2">não informado</p>
                  ) : (
                    <>
                      {/* As duas linhas existem SEMPRE, informadas ou não. Nas competências
                          anteriores à migration 036 a linha guarda só a efetiva, e é aqui que
                          isso fica visível — o sistema sabe que divergiu e não sabe de onde.
                          Nunca presume rat=3/fap=1,0 para fechar a conta: seria inventar a
                          origem da divergência, que é o que decide a defesa. */}
                      <div className="flex items-baseline justify-between gap-2 min-h-[1.75rem]">
                        <span className="text-[11px] text-gray-600">RAT base</span>
                        {espelho.enquadramento.rat_base_aplicado != null
                          ? <span className="text-sm font-semibold text-gray-900 tabular-nums">{fmt.pct(espelho.enquadramento.rat_base_aplicado)}</span>
                          : <NaoInformado />}
                      </div>
                      <div className="flex items-baseline justify-between gap-2 min-h-[1.75rem]">
                        <span className="text-[11px] text-gray-600">× FAP</span>
                        {espelho.enquadramento.fap_aplicado != null
                          ? <span className="text-sm font-semibold text-gray-900 tabular-nums">{fmt.num(espelho.enquadramento.fap_aplicado, 4)}</span>
                          : <NaoInformado />}
                      </div>
                      {/* O RÓTULO NÃO DECIDE O QUE O QUADRO AO LADO DIZ NÃO SABER (Carolina,
                          24/10). Chamar o número de "alíquota efetiva aplicada" é afirmar que
                          ele é a efetiva — exatamente a leitura que produz +1,50 p.p. de crédito
                          — enquanto a caixa da direita declara que não dá para saber se é a
                          efetiva ou a base. Sem o desdobramento ele é "Valor declarado", e nada
                          além disso.
                          O rótulo é condicional e não fixo: COM o RAT base e o FAP informados, a
                          efetiva é conhecida e "alíquota efetiva aplicada" é o nome certo. Trocar
                          sempre perderia precisão onde não há ambiguidade nenhuma. */}
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <span className={derivLabel}>
                          {faltaDesdobramento(espelho.enquadramento.rat_base_aplicado, espelho.enquadramento.fap_aplicado)
                            ? "Valor declarado"
                            : "Alíquota efetiva aplicada"}
                        </span>
                        <div className={derivVal}>{fmt.pct(espelho.enquadramento.aliquota_aplicada)}</div>
                      </div>
                      {faltaDesdobramento(espelho.enquadramento.rat_base_aplicado, espelho.enquadramento.fap_aplicado) && (
                        <p className="text-[10px] text-gray-500 mt-2 leading-snug">
                          Não é possível saber se este valor é a alíquota base ou a efetiva, e a
                          origem da divergência não pode ser afirmada enquanto{" "}
                          {faltaDesdobramento(espelho.enquadramento.rat_base_aplicado, espelho.enquadramento.fap_aplicado)}.
                        </p>
                      )}
                    </>
                  )}
                  {/* PROCEDÊNCIA, não "origem" (Carolina, 25/10). A palavra passou a significar
                      duas coisas na mesma tela: aqui é DE ONDE O DADO VEIO; no quadro ao lado é
                      a CAUSA da divergência — grau ou FAP —, que é o que decide a tese. Duas
                      acepções lado a lado num documento que vira peça não se sustentam, e a
                      acepção que importa juridicamente é a outra. */}
                  <p className="text-[10px] text-gray-500 mt-1">Procedência: declarado no estabelecimento</p>
                </div>

                {/* Item 6: a divergência é o produto — é o número pelo qual o cliente paga.
                    Peso maior e posição de resultado. O rótulo em texto que acompanhava a cor
                    ("crédito a recuperar" / "passivo a regularizar") SAIU em 25/10: ele concluía
                    sobre o caso a partir de um mês. Confundir crédito com passivo num laudo é
                    grave — quem compensa crédito inexistente responde com multa —, e justamente
                    por isso a conclusão pertence a quem viu a série inteira, não a este cartão,
                    que mostra uma competência de sessenta. */}
                {/* TRÊS ESTADOS, e o do meio é novo (Carolina, 24/10). Antes havia dois: ou não
                    havia aplicado, ou a divergência era afirmada. Faltava o caso em que HÁ um
                    número aplicado mas ele não diz se é base ou efetiva — e aí este quadro
                    afirmava crédito enquanto o quadro ao lado, no mesmo cartão, admitia que a
                    origem não podia ser afirmada. Um cartão não pode dizer as duas coisas. */}
                {(() => {
                  const e = espelho.enquadramento;
                  // 'undefined' conta como NÃO confirmada, de propósito: se o frontend subir
                  // antes da API, a tela fica conservadora e deixa de afirmar. O erro barato é
                  // pedir um dado que já existe; o caro é afirmar crédito que não se sustenta.
                  const confirmada = e.divergencia_confirmada === true;
                  const leituras = leiturasDoAplicado(e.aliquota_aplicada, e.fap, e.aliquota_efetiva);
                  const d = e.divergencia_pp;

                  if (e.aliquota_aplicada == null) {
                    return (
                      <div className="rounded-lg border bg-gray-50 border-gray-200 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-2">Divergência</p>
                        <div className={`${derivVal} text-gray-400`}>—</div>
                        <p className="text-[10px] text-gray-500 mt-2 leading-snug">
                          Sem o aplicado informado não há comparação a fazer.
                        </p>
                      </div>
                    );
                  }

                  if (!confirmada) {
                    return (
                      <div className="rounded-lg border-2 bg-amber-50 border-amber-300 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-800 mb-2">
                          Divergência — não confirmada
                        </p>
                        <div className={`${derivVal} text-amber-700`}>—</div>
                        <p className="text-[11px] text-amber-900 mt-1 leading-snug">
                          Depende de informar o <b>RAT base</b> e o <b>FAP</b> aplicados.
                        </p>
                        {/* As duas leituras lado a lado. Mostrar ambas é o que impede a tela de
                            escolher por quem assina — e deixa evidente que a diferença entre
                            "crédito a recuperar" e "nada a recuperar" está num dado que falta. */}
                        {leituras && (
                          <div className="mt-2 rounded border border-amber-200 bg-white/70 px-2 py-1.5 font-mono text-[10px] leading-relaxed text-gray-700">
                            <div>{fmt.pct(e.aliquota_aplicada)} como <b>efetiva</b></div>
                            <div className="pl-3 text-red-700">→ {fmt.pp(leituras.comoEfetiva)}</div>
                            {leituras.comoBase != null && leituras.efetivaSeBase != null && (
                              <>
                                <div className="mt-0.5">{fmt.pct(e.aliquota_aplicada)} como <b>base</b></div>
                                <div className="pl-3 text-emerald-700">
                                  → {fmt.pct(leituras.efetivaSeBase)}
                                  {leituras.comoBase === 0 ? " · sem divergência" : ` · ${fmt.pp(leituras.comoBase)}`}
                                </div>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  }

                  return (
                    <div className={`rounded-lg border p-3 ${
                      d == null ? "bg-gray-50 border-gray-200"
                      : d > 0 ? "bg-blue-50 border-blue-200"
                      : d < 0 ? "bg-red-50 border-red-200"
                      : "bg-gray-50 border-gray-200"}`}>
                      {/* O QUADRO INFORMA A DIVERGÊNCIA DESTA COMPETÊNCIA E PARA AÍ (Carolina,
                          25/10). Saíram daqui a frase "A empresa recolheu acima do devido. Há
                          valor a recuperar." e o sufixo "— crédito" do título.
                          O motivo apareceu quando a memória da janela inteira foi emitida pela
                          primeira vez: das sessenta competências, 24 são de débito e 22 de
                          crédito. O quadro mostra UM mês, e a frase lia como conclusão sobre o
                          caso — afirmando "há valor a recuperar" num período em que, na maior
                          parte dos meses, há valor a pagar. Conclusão sobre a janela só pode sair
                          de quem olhou a janela inteira, e esse lugar é a memória de cálculo.
                          O sinal continua legível: sinal do número, cor, e o title, que diz
                          "nesta competência" de forma explícita. */}
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-2">
                        Divergência
                      </p>
                      <div className={d != null && d > 0 ? "text-blue-700" : d != null && d < 0 ? "text-red-700" : "text-gray-700"}>
                        <div className="text-2xl font-bold tabular-nums leading-tight"
                          title={d != null && d > 0 ? "Nesta competência a empresa recolheu acima do devido."
                                 : d != null && d < 0 ? "Nesta competência a empresa recolheu abaixo do devido."
                                 : undefined}>
                          {fmt.pp(d)}
                        </div>
                        {d === 0 && (
                          <p className="text-[11px] font-medium mt-1 leading-snug">Sem divergência.</p>
                        )}
                      </div>
                      {/* A ORIGEM DECIDE A TESE, e é por isso que ela aparece aqui e não só na
                          listagem. Divergência de FAP se defende com a publicação do fator e o
                          prazo de contestação; divergência de grau, com a atividade preponderante
                          e a contagem de empregados. São provas diferentes — e esta é a tela que
                          vira memória de cálculo.
                          Não aparece quando a divergência é zero: ali não há causa a atribuir. */}
                      {espelho.enquadramento.origem_divergencia
                        && espelho.enquadramento.origem_divergencia !== "nenhuma" && (
                        <div className="mt-2 pt-2 border-t border-blue-200/70">
                          <span className="inline-block rounded border border-blue-300 bg-white/70 px-2 py-0.5 text-[11px] font-semibold text-blue-900">
                            Origem da divergência: {espelho.enquadramento.origem_label || espelho.enquadramento.origem_divergencia}
                          </span>
                          {espelho.enquadramento.origem_explicacao && (
                            <p className="text-[11px] text-gray-600 mt-1 leading-snug">
                              {espelho.enquadramento.origem_explicacao}
                            </p>
                          )}
                          {/* Processo informado afasta o achado: o leiaute do eSocial só aceita
                              alíquota diversa da prevista havendo decisão que a ampare. */}
                          {espelho.enquadramento.amparada && (
                            <p className="text-[11px] text-gray-500 mt-1 leading-snug">
                              Há processo informado amparando a alíquota aplicada nesta origem.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}
            </>
            )}

            {/* O rodapé diz em que ESTADO a competência está e se alguém a conferiu — não como
                ela foi calculada. O método ("apurado pelo motor, pela atividade preponderante")
                é fundamentação de campo e vive no § do CNAE, que cita o dispositivo e explica a
                regra. Estado e método são perguntas diferentes, e num laudo a que importa é
                quem assina embaixo: conferir é ato de pessoa, e o sistema nunca se autodeclara
                conferido (migration 040). */}
            {/* SÓ com competência apurada. Na prévia o retorno não traz situação — e a frase
                saía como "Esta competência está . Nenhuma pessoa a conferiu.", afirmando um
                estado vazio sobre uma competência que ainda não existe. A prévia já se explica
                pela linha de cima e pelo motivo logo abaixo. */}
            {espelho.enquadramento.confirmado && (
            <div className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 mt-4">
              {/* O MOTIVO VEM ANTES de qualquer outra coisa quando a competência está em
                  conferência: "em conferência" sozinho manda o usuário procurar o que falta.
                  Duas pendências caem no mesmo estado e pedem ações opostas — a do motor se
                  resolve declarando atividade, FAP ou CNAE; a do aplicado, informando o que a
                  empresa recolheu. O texto vem do backend (enquadramento_situacao), para a tela
                  não manter uma segunda versão da mesma regra. */}
              <p className="text-xs text-gray-700">
                Esta competência está <b>{ESP_SIT[espelho.enquadramento.situacao] || espelho.enquadramento.situacao}</b>.{" "}
                {espelho.enquadramento.motivo_conferencia ? (
                  <>
                    {espelho.enquadramento.motivo_conferencia}
                    {/* Conferência que existia e deixou de valer: o nome não some em silêncio.
                        Acontece quando a competência foi conferida e depois se constatou que a
                        comparação não fechava. */}
                    {espelho.enquadramento.conferido_por && (
                      <span className="text-gray-500"> Havia conferência de {espelho.enquadramento.conferido_por}, que deixa de valer enquanto o dado faltar.</span>
                    )}
                  </>
                ) : espelho.enquadramento.conferido_por ? (
                  <>Conferida por {espelho.enquadramento.conferido_por}
                    {espelho.enquadramento.conferido_em && <> em {fmt.dataHora(espelho.enquadramento.conferido_em)}</>}.</>
                ) : espelho.enquadramento.rat_aplicavel === false ? (
                  <>Não havia RAT a apurar, então não há o que conferir.</>
                ) : (
                  <>Nenhuma pessoa a conferiu.</>
                )}
              </p>
              <a href="/estabelecimentos" className="text-xs text-teal-700 hover:underline whitespace-nowrap">
                {/* O LINK ACOMPANHA O ESTADO. No regime que afasta a apuração o texto ao lado diz
                    "não há o que conferir" e o link dizia "Conferir no relatório" — uma linha
                    contradizendo a outra, oferecendo um ato que não existe ali. */}
                {espelho.enquadramento.motivo_conferencia
                  ? "Informar em Estabelecimentos →"
                  : espelho.enquadramento.rat_aplicavel === false
                  ? "Ver no relatório de enquadramento →"
                  : "Conferir no relatório de enquadramento →"}
              </a>
            </div>
            )}

            {espelho.motivo && <p className="text-[11px] text-gray-400 mt-2">{espelho.motivo}</p>}
          </>
        )}
      </section>

      {/* CPRB — estado explícito de verificação (RF-0.163..0.166) */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 mb-4">
        <h2 className="text-sm font-bold text-gray-800 mb-1">CPRB — desoneração da folha</h2>
        {/* O § SAIU DESTA FRASE (Carolina, 26/10, ponto 1). O marcador indica valor que decorre
            de norma; "não confundir com o período de apuração" é instrução de tela, e pendurar o
            § nela sugere que a instrução tem fundamento legal. Os § passam a ficar onde há norma
            de verdade: nas proporções de cada ano e na regra do ano-calendário. */}
        <p className="text-[11px] text-gray-400 mb-3">
          O estado precisa ser explícito: um bloco vazio não diz se a empresa <b>não optou</b> ou se
          <b> ninguém verificou</b>. Não confundir com o período de apuração.
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

        {cprbStatus === "optante" && (() => {
          // Só o ano MAIS ANTIGO pode começar fora de janeiro: é o primeiro ano com receita
          // apurada, de empresa que inicia atividade no curso do ano. Nos anos seguintes a opção
          // se manifesta no pagamento de janeiro, e não há o que escolher.
          const anoMaisAntigo = cprb.reduce<number | null>(
            (min, a) => (a.ano && (min === null || a.ano < min) ? a.ano : min), null);
          const regraDe = (ano: number | null) => cprbRegras.find((r: any) => r.ano === ano);
          return (
          <div className="border-t border-gray-100 pt-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-600">Anos de opção</span>
              <button type="button" disabled={cprbRegras.length === 0}
                onClick={() => setCprb((l) => [...l, { ano: null, parcial: false, mesInicio: "01" }])}
                className="text-[11px] text-teal-700 hover:underline disabled:opacity-40 disabled:no-underline">+ ano</button>
            </div>
            {/* A REGRA DO ANO-CALENDÁRIO, com o § que saiu da frase de ajuda. */}
            <p className="text-[11px] text-gray-500 mb-2 leading-snug">
              {cprbAvisos.anoCalendario
                || "A opção se manifesta no pagamento da CPRB de janeiro e é irretratável para todo o ano-calendário."}
              <Fundamentacao campo="cprb" em={hojeISO()} />
            </p>

            {cprbRegras.length === 0 && (
              <p className="text-xs text-amber-700">
                As regras de cada ano ainda não carregaram. Recarregue a página antes de declarar a opção.
              </p>
            )}
            {cprbRegras.length > 0 && cprb.length === 0 && (
              <p className="text-xs text-gray-500">Nenhum ano declarado. Adicione ao menos um.</p>
            )}

            {cprb.length > 0 && (
              <div className="grid grid-cols-[7rem_1fr_1fr_auto] gap-2 text-[10px] font-semibold uppercase tracking-wide text-gray-500 px-1 mb-1">
                <div>Ano</div><div>CPRB sobre a receita</div><div>Incisos I e III sobre a folha</div><div></div>
              </div>
            )}
            {cprb.map((a, i) => {
              const r = regraDe(a.ano);
              const ehPrimeiro = a.ano !== null && a.ano === anoMaisAntigo;
              return (
                <div key={i} className="mb-2">
                  <div className="grid grid-cols-[7rem_1fr_1fr_auto] gap-2 items-center">
                    <select className={inputCls} value={a.ano ?? ""}
                      onChange={(e) => setCprb((l) => l.map((x, j) => j === i
                        ? { ...x, ano: e.target.value ? Number(e.target.value) : null } : x))}>
                      <option value="">— ano —</option>
                      {[...cprbRegras].sort((x: any, y: any) => y.ano - x.ano).map((o: any) => (
                        <option key={o.ano} value={o.ano}>{o.ano}</option>
                      ))}
                    </select>
                    {/* As PROPORÇÕES são valor que decorre de norma, e é aqui que o § pertence.
                        Resolvido na data daquele ano: a redação que governa 2025 não é
                        necessariamente a que governa 2027. */}
                    <div className="text-xs text-gray-700">
                      {r ? <>{r.cprb_percentual.toLocaleString("pt-BR")}% da alíquota do setor
                        <Fundamentacao campo="cprb" em={`${a.ano}-12-01`} /></> : "—"}
                    </div>
                    <div className="text-xs text-gray-700">
                      {r ? (r.coexiste
                        ? <>{r.folha_percentual.toLocaleString("pt-BR")}% dos incisos I e III — {fmt.pct(r.folha_efetiva)}
                            <Fundamentacao campo="cprb" em={`${a.ano}-12-01`} /></>
                        : <span className="text-gray-400">sem patronal parcial neste ano</span>) : "—"}
                    </div>
                    <button type="button" className="text-red-400 text-sm px-1"
                      onClick={() => setCprb((l) => l.filter((_, j) => j !== i))}>✕</button>
                  </div>
                  {/* O MÊS só existe no primeiro ano com receita apurada. */}
                  {ehPrimeiro && (
                    <label className="flex flex-wrap items-center gap-1 text-[11px] text-gray-600 mt-1 ml-1">
                      <input type="checkbox" checked={a.parcial}
                        onChange={(e) => setCprb((l) => l.map((x, j) => j === i
                          ? { ...x, parcial: e.target.checked, mesInicio: e.target.checked ? x.mesInicio : "01" } : x))} />
                      primeiro ano com receita apurada — a opção começa em
                      <select className="border border-gray-300 rounded px-1 py-0.5 text-[11px] disabled:opacity-40"
                        disabled={!a.parcial} value={a.mesInicio}
                        onChange={(e) => setCprb((l) => l.map((x, j) => j === i ? { ...x, mesInicio: e.target.value } : x))}>
                        {MESES_NUM.map((m, k) => <option key={m} value={m}>{MESES[k]}</option>)}
                      </select>
                    </label>
                  )}
                </div>
              );
            })}

            {/* A RESSALVA DO DÉCIMO TERCEIRO. Faltava, e sem ela quem calculasse a patronal pela
                linha de apoio aplicaria 5% sobre uma folha que inclui o 13º — cobrando a mais em
                três exercícios. O RAT não entra nessa regra, e dizer isso evita o erro inverso. */}
            {cprb.some((a) => regraDe(a.ano)?.sem_decimo_terceiro) && (
              <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 mt-2">
                <p className="text-[11px] text-amber-900 leading-snug">
                  {cprbAvisos.decimo}
                  <Fundamentacao campo="cprb" em={hojeISO()} />
                </p>
              </div>
            )}
          </div>
          );
        })()}

        {/* AUTORIA NO PADRÃO DO REGIME (ponto 2): nome e hora, nos dois estados verificados.
            Saía "Última verificação: talhack@yahoo.com em 26/10/2026" — e-mail e sem hora —
            enquanto o bloco de Regime, na mesma página, já mostrava nome e hora. */}
        {cprbStatus !== "nao_informado" && cprbVerif.por && (
          <p className="text-[11px] text-gray-500 mt-3">
            Verificado por <b>{cprbVerif.por}</b>
            {cprbVerif.em ? <> em {fmt.dataHora(cprbVerif.em)}</> : null}.
          </p>
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
