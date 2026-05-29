// ==============================================================
// SST ESOCIAL GOV — React Query Hooks
// Arquivo: frontend/src/hooks/useQueries.ts
// ==============================================================

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  documentosApi, trabalhadoresApi, agentesApi,
  examesApi, catApi, validacoesApi, auditoriaApi
} from "../api/client";
import toast from "react-hot-toast";

// ---- DOCUMENTOS ----
export function useDocumentos(tipo?: string) {
  return useQuery({
    queryKey: ["documentos", tipo],
    queryFn: () => documentosApi.listar(tipo).then((r) => r.data),
  });
}

export function useDocumento(id: string) {
  return useQuery({
    queryKey: ["documentos", id],
    queryFn: () => documentosApi.obter(id).then((r) => r.data),
    enabled: !!id,
  });
}

export function useUploadDocumento() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => documentosApi.upload(formData).then((r) => r.data),
    onSuccess: () => {
      toast.success("Documento enviado com sucesso!");
      qc.invalidateQueries({ queryKey: ["documentos"] });
    },
    onError: () => toast.error("Erro ao enviar documento."),
  });
}

export function useSolicitarValidacao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentosApi.validar(id).then((r) => r.data),
    onSuccess: () => {
      toast.success("Validação IA iniciada!");
      qc.invalidateQueries({ queryKey: ["validacoes"] });
    },
    onError: () => toast.error("Erro ao iniciar validação."),
  });
}

// ---- TRABALHADORES ----
export function useTrabalhadores() {
  return useQuery({
    queryKey: ["trabalhadores"],
    queryFn: () => trabalhadoresApi.listar().then((r) => r.data),
  });
}

export function useTrabalhador(id: string) {
  return useQuery({
    queryKey: ["trabalhadores", id],
    queryFn: () => trabalhadoresApi.obter(id).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCriarTrabalhador() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: object) => trabalhadoresApi.criar(data).then((r) => r.data),
    onSuccess: () => {
      toast.success("Trabalhador cadastrado!");
      qc.invalidateQueries({ queryKey: ["trabalhadores"] });
    },
    onError: () => toast.error("Erro ao cadastrar trabalhador."),
  });
}

// ---- AGENTES NOCIVOS ----
export function useAgentesNocivos() {
  return useQuery({
    queryKey: ["agentes"],
    queryFn: () => agentesApi.listar().then((r) => r.data),
  });
}

// ---- EXAMES MÉDICOS ----
export function useExames() {
  return useQuery({
    queryKey: ["exames"],
    queryFn: () => examesApi.listar().then((r) => r.data),
  });
}

// ---- CAT ----
export function useCats() {
  return useQuery({
    queryKey: ["cat"],
    queryFn: () => catApi.listar().then((r) => r.data),
  });
}

// ---- VALIDAÇÕES IA ----
export function useValidacoes() {
  return useQuery({
    queryKey: ["validacoes"],
    queryFn: () => validacoesApi.listar().then((r) => r.data),
  });
}

export function useValidacao(id: string) {
  return useQuery({
    queryKey: ["validacoes", id],
    queryFn: () => validacoesApi.obter(id).then((r) => r.data),
    enabled: !!id,
  });
}

// ---- AUDITORIA ----
export function useAuditoria(tabela?: string) {
  return useQuery({
    queryKey: ["auditoria", tabela],
    queryFn: () => auditoriaApi.listar(tabela).then((r) => r.data),
  });
}
