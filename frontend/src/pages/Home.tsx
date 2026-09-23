// ==============================================================
// RadarPrevi — Home (Início): faixa executiva + cards de módulo
// ==============================================================
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Building2, Receipt, Activity, DollarSign, ListChecks, AlertTriangle, ArrowRight,
} from "lucide-react";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";

const BRL = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });

export function Home() {
  const { user } = useAuthStore();

  const { data: achados } = useQuery({
    queryKey: ["achados"],
    queryFn: () => apiClient.get("/achados/").then((r) => r.data),
  });
  const { data: diag } = useQuery({
    queryKey: ["diagnostico-blocos"],
    queryFn: () => apiClient.get("/diagnostico/blocos").then((r) => r.data),
  });

  const credito = achados?.total_credito ?? 0;
  const passivo = achados?.total_passivo ?? 0;
  const diverg = diag?.resumo?.blocos_divergentes ?? 0;
  const pend = diag?.resumo?.blocos_pendentes ?? 0;

  const cards = [
    { to: "/empresa", icon: Building2, title: "Cadastro da Empresa", desc: "Identificação, enquadramento e estabelecimentos." },
    { to: "/folha", icon: Receipt, title: "Folha de Pagamento", desc: "Lançamento e conciliação das rubricas." },
    { to: "/diagnostico", icon: Activity, title: "Diagnóstico de Custeio", desc: "O que se paga vs. o enquadramento correto." },
    { to: "/achados", icon: DollarSign, title: "Créditos", desc: "Recuperação retroativa corrigida pela SELIC.", stat: BRL(credito), pos: true },
    { to: "/achados", icon: AlertTriangle, title: "Passivo & Risco", desc: "Exposição quando se recolhe a menos que o devido.", stat: BRL(passivo), neg: true },
    { to: "/classificacao", icon: ListChecks, title: "Classificação", desc: "Rubricas condicionais que exigem decisão humana." },
  ];

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="mb-7">
        <div className="text-xs uppercase tracking-wider text-brand-600 font-semibold capitalize">{hoje}</div>
        <h1 className="font-serif text-3xl font-medium text-ink mt-1">Olá, {user?.nome?.split(" ")[0] ?? "bem-vindo"}</h1>
        <p className="text-muted mt-1">Visão geral do custeio previdenciário da empresa.</p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 rounded-xl border border-line bg-surface overflow-hidden">
        <div className="p-5 border-b md:border-b-0 md:border-r border-line">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted">
            <span className="w-1.5 h-1.5 rounded-sm bg-credit" /> Créditos identificados
          </div>
          <div className="font-serif text-3xl font-medium text-credit mt-2 tabular-nums">{BRL(credito)}</div>
          <div className="text-xs text-muted mt-2">Recuperação retroativa · corrigida pela SELIC</div>
        </div>
        <div className="p-5 border-b md:border-b-0 md:border-r border-line">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted">
            <span className="w-1.5 h-1.5 rounded-sm bg-risk" /> Exposição / passivo
          </div>
          <div className="font-serif text-3xl font-medium text-risk mt-2 tabular-nums">{BRL(passivo)}</div>
          <div className="text-xs text-muted mt-2">INSS a recolher · risco identificado</div>
        </div>
        <div className="p-5">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted">
            <span className="w-1.5 h-1.5 rounded-sm bg-brand-600" /> Pendências
          </div>
          <div className="font-serif text-3xl font-medium text-ink mt-2 tabular-nums">{diverg + pend}</div>
          <div className="text-xs text-muted mt-2">{diverg} divergência(s) · {pend} bloco(s) sem informação</div>
        </div>
      </div>

      {/* Módulos */}
      <div className="flex items-baseline gap-3 mt-8 mb-4">
        <h2 className="font-serif text-lg font-semibold text-ink">Módulos</h2>
        <span className="flex-1 h-px bg-line" />
        <span className="text-xs text-faint">cada área, um cartão</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {cards.map((c) => (
          <Link key={c.title + c.to} to={c.to}
            className="group bg-surface border border-line rounded-xl p-5 hover:border-line2 hover:shadow-sm transition-all">
            <c.icon size={30} strokeWidth={1.5} className="text-ink2 mb-3" />
            <h3 className="font-serif text-base font-semibold text-ink">{c.title}</h3>
            <p className="text-sm text-muted mt-1 leading-snug">{c.desc}</p>
            <div className="mt-3.5 pt-3 border-t border-line flex items-center justify-between">
              <span className={`text-sm font-semibold tabular-nums ${c.pos ? "text-credit" : c.neg ? "text-risk" : "text-muted"}`}>
                {c.stat ?? "Abrir"}
              </span>
              <ArrowRight size={17} className="text-faint group-hover:text-brand-600 transition-colors" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
