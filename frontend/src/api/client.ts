// ==============================================================
// SST ESOCIAL GOV — API Client (Axios + JWT interceptors)
// Arquivo: frontend/src/api/client.ts
// ==============================================================

import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

export const apiClient = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Request interceptor: adiciona JWT
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("sst_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: trata 401 (token expirado)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("sst_access_token");
      localStorage.removeItem("sst_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ---- API Endpoints ----

export const authApi = {
  login: (email: string, senha: string) =>
    apiClient.post("/auth/token", new URLSearchParams({ username: email, password: senha }), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  me: () => apiClient.get("/auth/me"),
};

export const documentosApi = {
  listar: (tipo?: string) => apiClient.get("/documentos/", { params: { tipo } }),
  obter: (id: string) => apiClient.get(`/documentos/${id}`),
  upload: (formData: FormData) =>
    apiClient.post("/documentos/upload/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  validar: (id: string) => apiClient.post(`/documentos/${id}/validar`),
};

export const trabalhadoresApi = {
  listar: () => apiClient.get("/trabalhadores/"),
  obter: (id: string) => apiClient.get(`/trabalhadores/${id}`),
  criar: (data: object) => apiClient.post("/trabalhadores/", data),
};

export const agentesApi = {
  listar: () => apiClient.get("/agentes/"),
  criar: (data: object) => apiClient.post("/agentes/", data),
};

export const examesApi = {
  listar: () => apiClient.get("/exames/"),
  criar: (data: object) => apiClient.post("/exames/", data),
};

export const catApi = {
  listar: () => apiClient.get("/cat/"),
  registrar: (data: object) => apiClient.post("/cat/", data),
};

export const validacoesApi = {
  listar: () => apiClient.get("/validacoes/"),
  obter: (id: string) => apiClient.get(`/validacoes/${id}`),
  feedback: (id: string, data: object) => apiClient.post(`/validacoes/${id}/feedback/`, data),
};

export const auditoriaApi = {
  listar: (tabela?: string) => apiClient.get("/auditoria/", { params: { tabela } }),
};
