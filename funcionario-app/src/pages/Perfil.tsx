import { User, LogOut, Shield } from "lucide-react";

export default function Perfil() {
  const user = JSON.parse(localStorage.getItem("radar_func_user") || "{}");

  const handleLogout = () => {
    localStorage.removeItem("radar_func_token");
    localStorage.removeItem("radar_func_user");
    window.location.href = "/login";
  };

  const formatCPF = (cpf: string) => {
    if (!cpf) return "—";
    return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
  };

  return (
    <div className="min-h-screen bg-[#f5f6fa] pb-24">
      <div className="bg-[#0f2744] text-white px-5 pt-12 pb-6">
        <h1 className="text-2xl font-bold">Perfil</h1>
        <p className="text-blue-300 text-sm mt-0.5">Seus dados e configurações</p>
      </div>
      <div className="px-4 mt-4 space-y-4">
        {/* Card perfil */}
        <div className="bg-white rounded-2xl p-5 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-[#1a9e8f] rounded-2xl flex items-center justify-center text-white text-2xl font-bold">
              {user.nome?.split(" ").map((n: string) => n[0]).slice(0, 2).join("") || "?"}
            </div>
            <div>
              <p className="font-bold text-gray-900 text-lg">{user.nome || "Funcionário"}</p>
              <p className="text-sm text-gray-500">CPF: {formatCPF(user.cpf)}</p>
            </div>
          </div>
        </div>

        {/* Segurança */}
        <div className="bg-white rounded-2xl p-4 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <Shield size={18} color="#1a9e8f" />
            <p className="font-semibold text-gray-900 text-sm">Segurança</p>
          </div>
          <p className="text-xs text-gray-500">
            Seus dados são protegidos e visíveis apenas para você e o RH da empresa.
          </p>
        </div>

        {/* Logout */}
        <button onClick={handleLogout}
          className="w-full bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-3">
          <LogOut size={20} color="#ef4444" />
          <p className="text-sm font-medium text-red-600">Sair do aplicativo</p>
        </button>
      </div>
    </div>
  );
}
