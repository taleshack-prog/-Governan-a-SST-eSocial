import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Home, Plus, MessageCircle, FolderOpen, User } from "lucide-react";
import MeuAfastamento from "./pages/MeuAfastamento";

// BYPASS TOTAL — token injetado diretamente
const BYPASS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ZTM1N2EwMS02NDY3LTQzMGItOGIxOS01MzJjMTcxZWU2NTciLCJ0aXBvIjoiZnVuY2lvbmFyaW8iLCJlbXByZXNhX2lkIjoiNGU1ZDkzYWEtZmUzOC00ZWNhLWJkOWYtOGVmYjNmMjYwMTJhIiwidHJhYmFsaGFkb3JfaWQiOiI3M2MwYzE1Ni0wYTE4LTRmMjgtYjE5NS02ODMyYjQzOWFlYTIiLCJleHAiOjE3ODA0MzY2NzV9.dpfxRRp14oJm0AohQevlODpqLfWWoVwgh9uRofWnE-c";
localStorage.setItem("radar_func_token", BYPASS_TOKEN);
localStorage.setItem("radar_func_user", JSON.stringify({
  nome: "Fabio Da Silva",
  cpf: "66565434400",
  trabalhador_id: "73c0c156-0a18-4f28-b195-6832b439aea2"
}));

function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const tabs = [
    { path: "/",            icon: Home,          label: "Início" },
    { path: "/afastamento", icon: Plus,          label: "Afastamentos" },
    { path: "/mensagens",   icon: MessageCircle, label: "Mensagens" },
    { path: "/documentos",  icon: FolderOpen,    label: "Documentos" },
    { path: "/perfil",      icon: User,          label: "Perfil" },
  ];
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40">
      <div className="flex justify-around py-2">
        {tabs.map(t => {
          const active = location.pathname === t.path;
          return (
            <button key={t.path} onClick={() => navigate(t.path)}
              className="flex flex-col items-center gap-0.5 px-3 py-1">
              <t.icon size={22} color={active ? "#0f2744" : "#9ca3af"} strokeWidth={active ? 2.5 : 1.5} />
              <span className={`text-xs ${active ? "text-[#0f2744] font-semibold" : "text-gray-400"}`}>
                {t.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<MeuAfastamento />} />
        <Route path="/afastamento" element={<MeuAfastamento />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
