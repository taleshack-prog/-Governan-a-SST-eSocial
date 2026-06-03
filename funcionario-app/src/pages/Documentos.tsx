import { FolderOpen, FileText } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export default function Documentos() {
  const user = JSON.parse(localStorage.getItem("radar_func_user") || "{}");

  const { data: afastamentos = [] } = useQuery({
    queryKey: ["docs-afastamentos"],
    queryFn: async () => {
      const token = localStorage.getItem("radar_func_token");
      const resp = await api.get("/funcionarios/auth/meus-afastamentos", {
        headers: { Authorization: `Bearer ${token}` }
      });
      return resp.data;
    },
  });

  return (
    <div className="min-h-screen bg-[#f5f6fa] pb-24">
      <div className="bg-[#0f2744] text-white px-5 pt-12 pb-6">
        <h1 className="text-2xl font-bold">Documentos</h1>
        <p className="text-blue-300 text-sm mt-0.5">Seus atestados e documentos</p>
      </div>
      <div className="px-4 mt-4 space-y-3">
        {afastamentos.length === 0 ? (
          <div className="bg-white rounded-2xl p-8 shadow-sm flex flex-col items-center gap-3">
            <FolderOpen size={48} color="#9ca3af" />
            <p className="text-gray-500 text-sm text-center">Nenhum documento encontrado.</p>
          </div>
        ) : (
          afastamentos.map((a: any) => (
            <div key={a.id} className="bg-white rounded-2xl p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
                  <FileText size={20} color="#3b82f6" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900 text-sm">Afastamento — {a.cid || "Sem CID"}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(a.data_inicio).toLocaleDateString("pt-BR")} •{" "}
                    {a.num_atestados || 0} atestado(s)
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
