import { useState } from "react";
import { api } from "../api/client";

export default function Login() {
  const [tela, setTela] = useState<"login" | "cadastro" | "troca">("login");
  const [cpf, setCpf] = useState("");
  const [senha, setSenha] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirma, setConfirma] = useState("");
  const [nome, setNome] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [telefone, setTelefone] = useState("");
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [loading, setLoading] = useState(false);
  const [bypass, setBypass] = useState(0);

  const formatCPF = (v: string) => {
    const n = v.replace(/\D/g, "").slice(0, 11);
    return n.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4")
            .replace(/(\d{3})(\d{3})(\d{3})/, "$1.$2.$3")
            .replace(/(\d{3})(\d{3})/, "$1.$2");
  };

  const formatCNPJ = (v: string) => {
    const n = v.replace(/\D/g, "").slice(0, 14);
    return n.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5")
            .replace(/(\d{2})(\d{3})(\d{3})(\d{4})/, "$1.$2.$3/$4")
            .replace(/(\d{2})(\d{3})(\d{3})/, "$1.$2.$3")
            .replace(/(\d{2})(\d{3})/, "$1.$2");
  };

  // Bypass oculto — toca 5x no logo
  const handleBypassTap = async () => {
    const next = bypass + 1;
    setBypass(next);
    if (next >= 5) {
      setBypass(0);
      setLoading(true);
      try {
        const resp = await api.post("/funcionarios/auth/login", {
          cpf: "66565434400",
          senha: "RADAR123",
        });
        localStorage.setItem("radar_func_token", resp.data.access_token);
        localStorage.setItem("radar_func_user", JSON.stringify(resp.data));
        window.location.href = "/";
      } catch {
        setCpf("665.654.344-00");
        setSenha("RADAR123");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleLogin = async () => {
    setErro(""); setLoading(true);
    try {
      const resp = await api.post("/funcionarios/auth/login", {
        cpf: cpf.replace(/\D/g, ""),
        senha,
      });
      localStorage.setItem("radar_func_token", resp.data.access_token);
      localStorage.setItem("radar_func_user", JSON.stringify(resp.data));
      if (resp.data.primeiro_acesso) {
        setTela("troca");
      } else {
        window.location.href = "/";
      }
    } catch (e: any) {
      setErro(e.response?.data?.detail || "CPF ou senha incorretos.");
    } finally {
      setLoading(false);
    }
  };

  const handleCadastro = async () => {
    setErro(""); setSucesso(""); setLoading(true);
    try {
      const resp = await api.post("/funcionarios/auth/cadastro", {
        cpf: cpf.replace(/\D/g, ""),
        nome,
        cnpj_empresa: cnpj,
        telefone,
      });
      setSucesso(resp.data.mensagem);
    } catch (e: any) {
      setErro(e.response?.data?.detail || "Erro ao enviar cadastro.");
    } finally {
      setLoading(false);
    }
  };

  const handleTrocarSenha = async () => {
    setErro(""); setLoading(true);
    if (novaSenha !== confirma) {
      setErro("As senhas não coincidem.");
      setLoading(false);
      return;
    }
    if (novaSenha.length < 6) {
      setErro("A senha deve ter pelo menos 6 caracteres.");
      setLoading(false);
      return;
    }
    try {
      await api.post("/funcionarios/auth/trocar-senha", {
        cpf: cpf.replace(/\D/g, ""),
        senha_atual: senha,
        nova_senha: novaSenha,
      });
      window.location.href = "/";
    } catch (e: any) {
      setErro(e.response?.data?.detail || "Erro ao trocar senha.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f2744] flex flex-col">
      {/* Header */}
      <div className="flex flex-col items-center pt-16 pb-10 px-6">
        <div onClick={handleBypassTap}
          className="w-16 h-16 bg-[#1a9e8f] rounded-2xl flex items-center justify-center mb-4 cursor-pointer select-none">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="2"/>
            <path d="M8 12l3 3 5-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <h1 className="text-white text-2xl font-bold">Radar Previdenciário</h1>
        <p className="text-blue-300 text-sm mt-1">
          {tela === "login" ? "Portal do Funcionário" :
           tela === "cadastro" ? "Solicitar acesso" :
           "Criar nova senha"}
        </p>
      </div>

      {/* Card */}
      <div className="flex-1 bg-white rounded-t-3xl px-6 pt-8 pb-10">

        {/* TELA LOGIN */}
        {tela === "login" && (
          <>
            <h2 className="text-xl font-bold text-gray-900 mb-1">Entrar</h2>
            <p className="text-sm text-gray-500 mb-6">Use seu CPF e senha fornecidos pelo RH</p>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">CPF</label>
                <input type="tel" placeholder="000.000.000-00" value={cpf}
                  onChange={e => setCpf(formatCPF(e.target.value))}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Senha</label>
                <input type="password" placeholder="Senha fornecida pelo RH" value={senha}
                  onChange={e => setSenha(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleLogin()}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              {erro && <div className="bg-red-50 border border-red-200 rounded-xl p-3"><p className="text-xs text-red-600">{erro}</p></div>}
              <button onClick={handleLogin} disabled={loading || !cpf || !senha}
                className="w-full bg-[#0f2744] text-white rounded-xl py-4 font-semibold text-sm disabled:opacity-50 active:scale-95 transition-transform">
                {loading ? "Entrando..." : "Entrar"}
              </button>
              <button onClick={() => { setTela("cadastro"); setErro(""); setSucesso(""); }}
                className="w-full border border-gray-300 text-gray-600 rounded-xl py-3.5 text-sm font-medium">
                Ainda não tenho acesso — Solicitar cadastro
              </button>
            </div>
          </>
        )}

        {/* TELA CADASTRO */}
        {tela === "cadastro" && (
          <>
            <h2 className="text-xl font-bold text-gray-900 mb-1">Solicitar acesso</h2>
            <p className="text-sm text-gray-500 mb-6">O RH irá aprovar e enviar sua senha</p>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Nome completo</label>
                <input type="text" placeholder="Seu nome completo" value={nome}
                  onChange={e => setNome(e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">CPF</label>
                <input type="tel" placeholder="000.000.000-00" value={cpf}
                  onChange={e => setCpf(formatCPF(e.target.value))}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">CNPJ da empresa</label>
                <input type="tel" placeholder="00.000.000/0001-00" value={cnpj}
                  onChange={e => setCnpj(formatCNPJ(e.target.value))}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Telefone (WhatsApp)</label>
                <input type="tel" placeholder="(51) 99999-9999" value={telefone}
                  onChange={e => setTelefone(e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              {erro && <div className="bg-red-50 border border-red-200 rounded-xl p-3"><p className="text-xs text-red-600">{erro}</p></div>}
              {sucesso && <div className="bg-green-50 border border-green-200 rounded-xl p-3"><p className="text-xs text-green-700">{sucesso}</p></div>}
              {!sucesso && (
                <button onClick={handleCadastro} disabled={loading || !nome || !cpf || !cnpj}
                  className="w-full bg-[#1a9e8f] text-white rounded-xl py-4 font-semibold text-sm disabled:opacity-50">
                  {loading ? "Enviando..." : "Solicitar cadastro"}
                </button>
              )}
              <button onClick={() => { setTela("login"); setErro(""); setSucesso(""); }}
                className="w-full text-gray-500 text-sm py-2">
                ← Voltar ao login
              </button>
            </div>
          </>
        )}

        {/* TELA TROCA DE SENHA */}
        {tela === "troca" && (
          <>
            <h2 className="text-xl font-bold text-gray-900 mb-1">Criar nova senha</h2>
            <p className="text-sm text-gray-500 mb-6">Este é seu primeiro acesso. Crie uma senha segura.</p>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Nova senha</label>
                <input type="password" placeholder="Mínimo 6 caracteres" value={novaSenha}
                  onChange={e => setNovaSenha(e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Confirmar senha</label>
                <input type="password" placeholder="Repita a senha" value={confirma}
                  onChange={e => setConfirma(e.target.value)}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-[#1a9e8f]" />
              </div>
              {erro && <div className="bg-red-50 border border-red-200 rounded-xl p-3"><p className="text-xs text-red-600">{erro}</p></div>}
              <button onClick={handleTrocarSenha} disabled={loading || !novaSenha || !confirma}
                className="w-full bg-[#0f2744] text-white rounded-xl py-4 font-semibold text-sm disabled:opacity-50">
                {loading ? "Salvando..." : "Salvar senha e entrar"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
