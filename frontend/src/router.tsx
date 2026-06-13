// ==============================================================
// SST ESOCIAL GOV — Router principal
// Arquivo: frontend/src/router.tsx
// ==============================================================

import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Documentos } from "./pages/Documentos";
import { Trabalhadores } from "./pages/Trabalhadores";
import { AgentesNocivos } from "./pages/AgentesNocivos";
import { ExamesMedicos } from "./pages/ExamesMedicos";
import { Cat } from "./pages/Cat";
import { ValidacoesIA } from "./pages/ValidacoesIA";
import { Auditoria } from "./pages/Auditoria";
import Afastamentos from "./pages/Afastamentos";
import Radar from "./pages/Radar";
import PPP from "./pages/PPP";
import PainelFinanceiro from "./pages/PainelFinanceiro";
import PainelGestor from "./pages/PainelGestor";
import AfastamentosRH from "./pages/AfastamentosRH";
import Admin from "./pages/Admin";
import RadarFinanceiro from "./pages/RadarFinanceiro";
import Inconsistencias from "./pages/Inconsistencias";
import Tendencias from "./pages/Tendencias";
import Importacao from "./pages/Importacao";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard",      element: <Dashboard /> },
      { path: "documentos",     element: <Documentos /> },
      { path: "trabalhadores",  element: <Trabalhadores /> },
      { path: "agentes",        element: <AgentesNocivos /> },
      { path: "exames",         element: <ExamesMedicos /> },
      { path: "afastamentos",   element: <Afastamentos /> },
      { path: "radar",           element: <Radar /> },
      { path: "ppp",             element: <PPP /> },
      { path: "painel-financeiro", element: <PainelFinanceiro /> },
      { path: "painel-gestor",     element: <PainelGestor /> },
      { path: "afastamentos-rh",   element: <AfastamentosRH /> },
      { path: "admin",             element: <Admin /> },
      { path: "radar-financeiro",   element: <RadarFinanceiro /> },
      { path: "inconsistencias",    element: <Inconsistencias /> },
      { path: "tendencias",          element: <Tendencias /> },
      { path: "importacao",          element: <Importacao /> },
      { path: "cat",            element: <Cat /> },
      { path: "validacoes",     element: <ValidacoesIA /> },
      { path: "auditoria",      element: <Auditoria /> },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/dashboard" replace />,
  },
]);
