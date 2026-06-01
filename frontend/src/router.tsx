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
