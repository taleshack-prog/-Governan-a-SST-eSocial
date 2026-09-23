// ==============================================================
// RadarPrevi — Sidebar (agrupada, retrátil, tema teal)
// ==============================================================
import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Home, Building2, Store, Receipt, Activity, DollarSign, ListChecks,
  FileText, ShieldAlert, Stethoscope, HeartPulse, ClipboardList, AlertOctagon,
  LayoutDashboard, Radar, TrendingDown, TrendingUp, Upload, UserCog,
  BriefcaseMedical, Brain, ScrollText, LogOut, ChevronsLeft, ChevronsRight,
  Sun, Moon,
} from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { getTheme, toggleTheme, type Theme } from "../lib/theme";

const GROUPS: { title: string | null; items: { path: string; label: string; icon: any; end?: boolean }[] }[] = [
  { title: null, items: [
    { path: "/", label: "Início", icon: Home, end: true },
  ]},
  { title: "Custeio", items: [
    { path: "/empresa", label: "Empresa", icon: Building2 },
    { path: "/estabelecimentos", label: "Estabelecimentos", icon: Store },
    { path: "/folha", label: "Folha de Pagamento", icon: Receipt },
    { path: "/diagnostico", label: "Diagnóstico", icon: Activity },
    { path: "/achados", label: "Créditos", icon: DollarSign },
    { path: "/classificacao", label: "Classificação", icon: ListChecks },
  ]},
  { title: "SST", items: [
    { path: "/documentos", label: "Documentos", icon: FileText },
    { path: "/agentes", label: "Agentes Nocivos", icon: ShieldAlert },
    { path: "/exames", label: "Exames Médicos", icon: Stethoscope },
    { path: "/afastamentos", label: "Afastamentos", icon: HeartPulse },
    { path: "/ppp", label: "PPP Digital", icon: ClipboardList },
    { path: "/cat", label: "CAT", icon: AlertOctagon },
  ]},
  { title: "Gestão", items: [
    { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { path: "/radar", label: "Radar Previd.", icon: Radar },
    { path: "/painel-financeiro", label: "Painel Financeiro", icon: DollarSign },
    { path: "/radar-financeiro", label: "Radar Financeiro", icon: TrendingDown },
    { path: "/inconsistencias", label: "Inconsistências", icon: ShieldAlert },
    { path: "/tendencias", label: "Tendências", icon: TrendingUp },
    { path: "/importacao", label: "Importar", icon: Upload },
    { path: "/painel-gestor", label: "Painel do Gestor", icon: UserCog },
    { path: "/afastamentos-rh", label: "Afastamentos RH", icon: BriefcaseMedical },
    { path: "/validacoes", label: "Validações IA", icon: Brain },
    { path: "/auditoria", label: "Auditoria", icon: ScrollText },
  ]},
];

function Mark({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden>
      <circle cx="24" cy="24" r="20" stroke="#5b6675" strokeWidth="1.4" />
      <circle cx="24" cy="24" r="13" stroke="#5b6675" strokeWidth="1.4" />
      <line x1="24" y1="3.5" x2="24" y2="44.5" stroke="#5b6675" strokeWidth="1" />
      <line x1="3.5" y1="24" x2="44.5" y2="24" stroke="#5b6675" strokeWidth="1" />
      <circle cx="24" cy="24" r="7.6" stroke="rgb(var(--c-brand-500))" strokeWidth="1.6" />
      <circle cx="24" cy="24" r="3.3" fill="rgb(var(--c-brand-500))" />
      <circle cx="35" cy="15" r="3.1" fill="rgb(var(--c-brand-500))" />
    </svg>
  );
}

export function Sidebar() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try { return localStorage.getItem("rp_sidebar") === "1"; } catch { return false; }
  });
  const [theme, setThemeState] = useState<Theme>(getTheme());

  function toggleCollapsed() {
    setCollapsed((c) => {
      const n = !c;
      try { localStorage.setItem("rp_sidebar", n ? "1" : "0"); } catch {}
      return n;
    });
  }
  function onToggleTheme() { setThemeState(toggleTheme()); }
  function handleLogout() { clearAuth(); navigate("/login"); }

  return (
    <aside className={`${collapsed ? "w-[72px]" : "w-64"} shrink-0 h-full bg-sidebar text-sidebar-ink flex flex-col transition-[width] duration-200`}>
      {/* Marca */}
      <div className={`flex items-center gap-3 px-4 py-4 border-b border-white/10 ${collapsed ? "justify-center" : ""}`}>
        <Mark />
        {!collapsed && (
          <div className="leading-none">
            <div className="font-bold tracking-[0.11em] text-white text-[15px]">
              RADAR<span className="text-brand-500 ml-0.5">PREVI</span>
            </div>
            <div className="text-[9px] tracking-[0.22em] uppercase text-sidebar-muted mt-1">Consultoria Previdenciária</div>
          </div>
        )}
      </div>

      {/* Recolher / expandir */}
      <button
        onClick={toggleCollapsed}
        title={collapsed ? "Expandir" : "Recolher"}
        className="flex items-center justify-center gap-2 py-2 border-b border-white/10 text-sidebar-muted hover:text-white hover:bg-white/5 transition-colors"
      >
        {collapsed ? <ChevronsRight size={16} /> : <><ChevronsLeft size={16} /><span className="text-xs">Recolher</span></>}
      </button>

      {/* Navegação */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {GROUPS.map((g, gi) => (
          <div key={gi} className="mb-1">
            {g.title && !collapsed && (
              <div className="text-[10px] tracking-[0.18em] uppercase text-sidebar-muted px-3 pt-4 pb-1.5">{g.title}</div>
            )}
            {g.title && collapsed && <div className="h-px bg-white/10 mx-3 my-3" />}
            {g.items.map(({ path, label, icon: Icon, end }) => (
              <NavLink
                key={path}
                to={path}
                end={end}
                title={collapsed ? label : undefined}
                className={({ isActive }) =>
                  `group flex items-center gap-3 rounded-lg text-sm py-2.5 transition-colors ${
                    collapsed ? "justify-center w-11 mx-auto px-0" : "px-3"
                  } ${isActive ? "bg-white/10 text-white font-medium" : "text-sidebar-ink hover:bg-white/5"}`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} className={isActive ? "text-brand-500" : "text-sidebar-muted group-hover:text-sidebar-ink"} />
                    {!collapsed && <span className="flex-1 truncate">{label}</span>}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Tema */}
      <button
        onClick={onToggleTheme}
        title="Alternar tema claro/escuro"
        className={`flex items-center gap-3 mx-2 my-1.5 rounded-lg border border-white/10 py-2.5 hover:bg-white/5 transition-colors ${collapsed ? "justify-center px-0" : "px-3"}`}
      >
        {theme === "dark"
          ? <Moon size={17} className="text-brand-500" />
          : <Sun size={17} className="text-brand-500" />}
        {!collapsed && <span className="text-[13px]">{theme === "dark" ? "Tema escuro" : "Tema claro"}</span>}
      </button>

      {/* Usuário */}
      <div className={`flex items-center gap-3 px-4 py-3 border-t border-white/10 ${collapsed ? "justify-center" : ""}`}>
        <div className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold shrink-0">
          {user?.nome?.[0]?.toUpperCase() ?? "U"}
        </div>
        {!collapsed && (
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.nome ?? "Usuário"}</p>
            <button onClick={handleLogout} className="flex items-center gap-1.5 text-xs text-sidebar-muted hover:text-white transition-colors mt-0.5">
              <LogOut size={13} /> Sair
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
