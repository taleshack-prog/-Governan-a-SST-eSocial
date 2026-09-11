// ==============================================================
// SST ESOCIAL GOV — Abertura inteligente
// Decide a tela inicial: se o cadastro está incompleto → Estabelecimentos (onboarding);
// se já configurado → Diagnóstico (o valor). Reusa GET /empresas/{id}/cadastro-status.
// ==============================================================
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";

export function AberturaInteligente() {
  const navigate = useNavigate();
  const [carregando, setCarregando] = useState(true);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    let ativo = true;
    const decidir = async () => {
      try {
        const empresaId = user?.empresa_id;
        if (!empresaId) {
          navigate("/diagnostico", { replace: true });
          return;
        }
        const resp = await apiClient.get(`/empresas/${empresaId}/cadastro-status`);
        const completo = resp.data?.completo;
        const faltando: string[] = resp.data?.faltando || [];
        if (!ativo) return;
        if (completo) {
          navigate("/diagnostico", { replace: true });
        } else {
          // se falta algum dado da EMPRESA (CNAE/FPAS/regime/CNPJ) → cadastro da empresa
          const faltaEmpresa = faltando.some((f) => f.toLowerCase().includes("empresa"));
          navigate(faltaEmpresa ? "/empresa" : "/estabelecimentos", { replace: true });
        }
      } catch {
        // em caso de erro, cai no diagnóstico (não trava o usuário)
        if (ativo) navigate("/diagnostico", { replace: true });
      } finally {
        if (ativo) setCarregando(false);
      }
    };
    decidir();
    return () => { ativo = false; };
  }, [navigate, user]);

  return (
    <div className="p-8 text-center text-gray-400">
      {carregando ? "Preparando seu painel..." : ""}
    </div>
  );
}
