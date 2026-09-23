// ==============================================================
// RADAR PREVIDENCIÁRIO — Layout Principal
// Arquivo: frontend/src/components/Layout.tsx
// ==============================================================

import { Outlet, Navigate } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useAuthStore } from "../store/authStore";
import PrevIA from "./PrevIA";

export function Layout() {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-y-auto p-8">
        <Outlet />
      </main>
      <PrevIA />
    </div>
  );
}
