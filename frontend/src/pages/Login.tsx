// ==============================================================
// SST ESOCIAL GOV — Página: Login
// Arquivo: frontend/src/pages/Login.tsx
// ==============================================================

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { authApi } from "../api/client";
import { useAuthStore } from "../store/authStore";
import toast from "react-hot-toast";

const schema = z.object({
  email: z.string().email("E-mail inválido"),
  senha: z.string().min(6, "Senha deve ter ao menos 6 caracteres"),
});

type FormData = z.infer<typeof schema>;

// A FRASE CERTA PARA CADA FALHA (04/11).
//
// Esta tela dizia "Credenciais inválidas." para QUALQUER erro, inclusive quando a requisição
// nunca saiu do navegador. Em 04/11 a Carolina não conseguiu entrar pela rede do Ministério
// Público, que bloqueia o endereço da API: a tela anunciou senha errada, e nós passamos uma hora
// investigando autenticação, RLS e versões de dependência antes de descobrir que era firewall.
// Uma mensagem de erro que mente sobre a causa é pior do que uma mensagem genérica, porque
// manda quem lê para o lugar errado com confiança.
//
// A distinção é objetiva: ou existe 'response', e então o servidor respondeu e o que ele disse
// é a verdade; ou não existe, e então ninguém respondeu — rede, DNS, proxy corporativo, ou o
// servidor fora do ar. São estados diferentes e pedem frases diferentes.
function mensagemDeFalhaDeLogin(err: any): string {
  const detalhe = err?.response?.data?.detail;
  if (typeof detalhe === "string" && detalhe.trim()) return detalhe.trim();
  if (err?.response) return "Credenciais inválidas.";
  if (err?.code === "ECONNABORTED") {
    return "O servidor demorou demais para responder. Tente novamente em alguns instantes.";
  }
  return "Não foi possível falar com o servidor. Verifique sua conexão — e, se você estiver "
       + "numa rede corporativa, é possível que ela bloqueie o acesso ao sistema.";
}

export function Login() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setLoading(true);
    try {
      const res = await authApi.login(data.email, data.senha);
      const { access_token, user_id, nome, perfil, empresa_id } = res.data;
      setAuth({ id: user_id, nome, email: data.email, perfil, empresa_id }, access_token);
      toast.success(`Bem-vindo, ${nome}!`);
      navigate("/");
    } catch (err: any) {
      toast.error(mensagemDeFalhaDeLogin(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-indigo-950 to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          {/* Só a marca. O ícone genérico e a linha "Inteligência Previdenciária com IA" saíram:
              a tagline agora faz parte do próprio logo, e repetir outra abaixo dela punha duas
              descrições concorrentes do que o produto é. */}
          <img src="/logo-ajusta.svg" alt="Ajusta — Defesa Previdenciária Empresarial"
               className="w-full max-w-sm mx-auto" />
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Entrar no sistema</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
              <input
                {...register("email")}
                type="email"
                placeholder="seu@email.com"
                className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
              <input
                {...register("senha")}
                type="password"
                placeholder="••••••••"
                className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              {errors.senha && <p className="text-red-500 text-xs mt-1">{errors.senha.message}</p>}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? <><Loader2 size={18} className="animate-spin" /> Entrando...</> : "Entrar"}
            </button>
          </form>

          <p className="text-center text-xs text-gray-400 mt-6">
            Sistema restrito — acesso somente a usuários autorizados.
          </p>
        </div>
      </div>
    </div>
  );
}
