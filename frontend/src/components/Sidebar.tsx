// ==============================================================
// RADAR PREVIDENCIÁRIO — Sidebar de Navegação
// Arquivo: frontend/src/components/Sidebar.tsx
// ==============================================================

import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FileText, Users, ShieldAlert,
  Stethoscope, AlertOctagon, Brain, ScrollText,
  LogOut, ChevronRight, Activity, HeartPulse, Radar, ClipboardList, DollarSign, UserCog, BriefcaseMedical, Building2, TrendingDown, Upload, FileText,
} from "lucide-react";
import { useAuthStore } from "../store/authStore";

const NAV_ITEMS = [
  { path: "/dashboard",    label: "Dashboard",       icon: LayoutDashboard },
  { path: "/documentos",   label: "Documentos",      icon: FileText },
  { path: "/trabalhadores",label: "Trabalhadores",   icon: Users },
  { path: "/agentes",      label: "Agentes Nocivos", icon: ShieldAlert },
  { path: "/exames",       label: "Exames Médicos",  icon: Stethoscope },
  { path: "/afastamentos", label: "Afastamentos",    icon: HeartPulse },
  { path: "/radar",         label: "Radar Previd.",   icon: Radar },
  { path: "/painel-financeiro", label: "Painel Financeiro", icon: DollarSign },
  { path: "/radar-financeiro",   label: "Radar Financeiro",  icon: TrendingDown },
  { path: "/inconsistencias",     label: "Inconsistências",   icon: ShieldAlert },
  { path: "/tendencias",          label: "Tendências",        icon: Activity },
  { path: "/importacao",          label: "Importar Dados",    icon: Upload },
  { path: "/importacao-pdf",      label: "Importar LTCAT",    icon: FileText },
  { path: "/painel-gestor",     label: "Painel do Gestor",  icon: UserCog },
  { path: "/afastamentos-rh",   label: "Afastamentos RH",   icon: BriefcaseMedical },
  { path: "/ppp",           label: "PPP Digital",     icon: ClipboardList },
  { path: "/cat",          label: "CAT",             icon: AlertOctagon },
  { path: "/validacoes",   label: "Validações IA",   icon: Brain },
  { path: "/auditoria",    label: "Auditoria",       icon: ScrollText },
];

export function Sidebar() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  function handleLogout() {
    clearAuth();
    navigate("/login");
  }

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900 text-white flex flex-col z-30">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-gray-700">
        <img src="/logo-radarprevi.svg" alt="Radar Previdenciário" className="h-12 w-auto" />
      </div>

      {/* Navegação */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              }`
            }
          >
            <Icon size={18} />
            <span className="flex-1">{label}</span>
            <ChevronRight size={14} className="opacity-40" />
          </NavLink>
        ))}
      </nav>

      {/* Usuário */}
      <div className="px-4 py-4 border-t border-gray-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-sm font-bold">
            {user?.nome?.[0]?.toUpperCase() ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.nome ?? "Usuário"}</p>
            <p className="text-xs text-gray-400 capitalize">{user?.perfil ?? "—"}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-xs text-gray-400 hover:text-white transition-colors w-full px-2 py-1.5 rounded hover:bg-gray-800"
        >
          <LogOut size={14} />
          Sair
        </button>
      </div>
    </aside>
  );
}
// cache bust sex 05 jun 2026 20:44:05 -03
// dom 14 jun 2026 18:03:04 -03
