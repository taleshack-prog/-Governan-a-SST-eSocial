// ==============================================================
// SST ESOCIAL GOV — Auth Store (Zustand)
// Arquivo: frontend/src/store/authStore.ts
// ==============================================================

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  nome: string;
  email: string;
  perfil: string;
  empresa_id: string | null;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user, token) => {
        localStorage.setItem("sst_access_token", token);
        set({ user, token, isAuthenticated: true });
      },

      clearAuth: () => {
        localStorage.removeItem("sst_access_token");
        localStorage.removeItem("sst_user");
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: "sst-esocial-auth",
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);
