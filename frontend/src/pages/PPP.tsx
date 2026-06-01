// ==============================================================
// SST ESOCIAL GOV — Página: PPP Digital
// Arquivo: frontend/src/pages/PPP.tsx
// ==============================================================

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

const COMPLETUDE_COR = (p: number) =>
  p === 100 ? "text-green-600 bg-green-50 border-green-200" :
  p >= 70   ? "text-orange-600 bg-orange-50 border-orange-200" :
              "text-red-600 bg-red-50 border-red-200";

const COMPLETUDE_LABEL = (p: number) =>
  p === 100 ? "✅ Completo" : p >= 70 ? "⚠️ Incompleto" : "🔴 Crítico";

export default function PPP() {
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [validando, setValidando] = useState(false);
  const [resultadoIA, setResultadoIA] = useState<any>(null);
  const [baixando, setBaixando] = useState(false);

  const baixarPDF = async (trabId: string, nome: string) => {
    setBaixando(true);
    try {
      const token = localStorage.getItem("sst_access_token") || "";
      const resp = await fetch(`http://localhost:8003/api/ppp/${trabId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error("Erro na API");
      const blob = new Blob([await resp.arrayBuffer()], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `PPP_${nome.replace(/ /g, "_")}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (e) {
      alert("Erro ao gerar PDF");
    } finally {
      setBaixando(false);
    }
  };

  const { data: ppps = [], isLoading } = useQuery({
    queryKey: ["ppps"],
    queryFn: () => apiClient.get("/ppp/").then(r => r.data),
  });

  const { data: pppDetalhe } = useQuery({
    queryKey: ["ppp", selecionado],
    queryFn: () => selecionado
      ? apiClient.get(`/ppp/${selecionado}/`).then(r => r.data)
      : null,
    enabled: !!selecionado,
  });

  const validarComIA = async (trabId: string) => {
    setValidando(true);
    setResultadoIA(null);
    try {
      const resp = await apiClient.get(`/ppp/${trabId}/validar/`);
      setResultadoIA(resp.data);
    } catch {
      setResultadoIA({ alertas: ["Erro na validação"], recomendacoes: [] });
    } finally {
      setValidando(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">📋 PPP Digital</h1>
        <p className="text-sm text-gray-500 mt-1">
          Perfil Profissiográfico Previdenciário — Lei 8.213/91 | IN INSS 128/2022
        </p>
      </div>

      {/* Info legal */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p className="text-xs font-bold text-blue-800 mb-1">📌 Base Legal</p>
        <p className="text-xs text-blue-700">
          O PPP é obrigatório desde 2004 e deve ser emitido pela empresa com base no LTCAT.
          Desde 2023, os registros ambientais são informados exclusivamente via eSocial S-2240.
          Conforme §1º art. 58 da Lei 8.213/1991 e art. 68 do Decreto 3.048/1999.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lista de trabalhadores */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-bold text-gray-700">Trabalhadores</h2>
          {isLoading ? (
            <div className="text-gray-400 text-sm">Carregando...</div>
          ) : ppps.length === 0 ? (
            <div className="text-gray-400 text-sm">Nenhum trabalhador cadastrado.</div>
          ) : (
            ppps.map((p: any) => (
              <div
                key={p.trabalhador_id}
                onClick={() => { setSelecionado(p.trabalhador_id); setResultadoIA(null); }}
                className={`border rounded-xl p-4 cursor-pointer transition-all ${
                  selecionado === p.trabalhador_id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-blue-300"
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-bold text-gray-900">{p.trabalhador_nome}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{p.cargo || "Cargo não informado"}</p>
                    <p className="text-xs text-gray-400">{p.setor || "Setor não informado"}</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full border font-medium ${COMPLETUDE_COR(p.completude.percentual)}`}>
                    {p.completude.percentual}%
                  </span>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full ${p.completude.percentual === 100 ? "bg-green-500" : p.completude.percentual >= 70 ? "bg-orange-400" : "bg-red-500"}`}
                      style={{ width: `${p.completude.percentual}%` }}
                    />
                  </div>
                  <p className="text-xs mt-1 font-medium">{COMPLETUDE_LABEL(p.completude.percentual)}</p>
                  {p.completude.pendencias.length > 0 && (
                    <p className="text-xs text-red-500 mt-1">
                      {p.completude.pendencias.length} pendência(s)
                    </p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Detalhe do PPP */}
        <div className="lg:col-span-2">
          {!selecionado ? (
            <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400">
              <p className="text-4xl mb-3">📋</p>
              <p className="text-sm">Selecione um trabalhador para ver o PPP</p>
            </div>
          ) : !pppDetalhe ? (
            <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400">
              Carregando PPP...
            </div>
          ) : (
            <div className="space-y-4">
              {/* Header do PPP */}
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h2 className="text-lg font-black text-gray-900">PPP — {pppDetalhe.trabalhador?.nome}</h2>
                    <p className="text-xs text-gray-500">Gerado em {new Date(pppDetalhe.gerado_em).toLocaleString("pt-BR")}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => validarComIA(selecionado)}
                      disabled={validando}
                      className="bg-purple-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-purple-700 disabled:opacity-50"
                    >
                      {validando ? "⏳ Validando..." : "🤖 Validar com IA"}
                    </button>
                    <button
                      onClick={() => baixarPDF(selecionado, pppDetalhe?.trabalhador?.nome || "PPP")}
                      disabled={baixando}
                      className="bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-green-700 disabled:opacity-50"
                    >
                      {baixando ? "⏳ Gerando..." : "📥 Baixar PDF"}
                    </button>
                  </div>
                </div>

                {/* Completude */}
                {pppDetalhe.completude && (
                  <div className={`rounded-lg p-3 border ${COMPLETUDE_COR(pppDetalhe.completude.percentual)}`}>
                    <div className="flex justify-between items-center mb-2">
                      <p className="text-xs font-bold">Completude do PPP</p>
                      <span className="text-lg font-black">{pppDetalhe.completude.percentual}%</span>
                    </div>
                    <div className="w-full bg-white/50 rounded-full h-2 mb-2">
                      <div
                        className="h-2 rounded-full bg-current opacity-70"
                        style={{ width: `${pppDetalhe.completude.percentual}%` }}
                      />
                    </div>
                    {pppDetalhe.completude.pendencias.length > 0 && (
                      <div className="space-y-1 mt-2">
                        {pppDetalhe.completude.pendencias.map((p: string, i: number) => (
                          <p key={i} className="text-xs">⚠️ {p}</p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Dados da Empresa */}
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <h3 className="text-xs font-bold text-gray-700 uppercase mb-3">I — Dados da Empresa</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><p className="text-xs text-gray-500">Razão Social</p><p className="font-medium">{pppDetalhe.empresa?.razao_social || "—"}</p></div>
                  <div><p className="text-xs text-gray-500">CNPJ</p><p className="font-medium font-mono">{pppDetalhe.empresa?.cnpj || "—"}</p></div>
                  <div><p className="text-xs text-gray-500">CNAE</p><p className="font-medium">{pppDetalhe.empresa?.cnae || "—"}</p></div>
                  <div><p className="text-xs text-gray-500">Grau de Risco</p><p className={`font-bold ${pppDetalhe.empresa?.grau_risco >= 3 ? "text-red-600" : "text-orange-500"}`}>{pppDetalhe.empresa?.grau_risco || "—"}</p></div>
                </div>
              </div>

              {/* Dados do Trabalhador */}
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <h3 className="text-xs font-bold text-gray-700 uppercase mb-3">II — Dados do Trabalhador</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><p className="text-xs text-gray-500">Nome</p><p className="font-medium">{pppDetalhe.trabalhador?.nome || "—"}</p></div>
                  <div><p className="text-xs text-gray-500">CPF</p><p className="font-medium font-mono">{pppDetalhe.trabalhador?.cpf || "—"}</p></div>
                  <div><p className="text-xs text-gray-500">Cargo</p><p className="font-medium">{pppDetalhe.trabalhador?.cargo || <span className="text-red-500">Não informado</span>}</p></div>
                  <div><p className="text-xs text-gray-500">Setor/GES</p><p className="font-medium">{pppDetalhe.trabalhador?.setor || <span className="text-red-500">Não informado</span>}</p></div>
                  <div><p className="text-xs text-gray-500">Admissão</p><p className="font-medium">{pppDetalhe.trabalhador?.data_admissao || <span className="text-red-500">Não informada</span>}</p></div>
                  <div><p className="text-xs text-gray-500">Sexo</p><p className="font-medium">{pppDetalhe.trabalhador?.sexo === "M" ? "Masculino" : pppDetalhe.trabalhador?.sexo === "F" ? "Feminino" : "—"}</p></div>
                </div>
              </div>

              {/* Agentes Nocivos */}
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <h3 className="text-xs font-bold text-gray-700 uppercase mb-3">
                  III — Registros Ambientais ({pppDetalhe.agentes_nocivos?.length || 0} agente(s))
                </h3>
                {pppDetalhe.agentes_nocivos?.length === 0 ? (
                  <p className="text-sm text-red-500">⚠️ Nenhum agente nocivo cadastrado</p>
                ) : (
                  <div className="space-y-2">
                    {pppDetalhe.agentes_nocivos?.map((a: any, i: number) => (
                      <div key={i} className={`rounded-lg p-3 border ${a.enquadramento_especial ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200"}`}>
                        <div className="flex justify-between items-center">
                          <div>
                            <span className="font-mono text-xs bg-white px-2 py-0.5 rounded border mr-2">{a.codigo_tabela24}</span>
                            <span className="text-xs font-medium text-gray-700">{a.descricao}</span>
                          </div>
                          <span className="text-xs font-bold">{a.nivel_exposicao || "Qualitativo"}</span>
                        </div>
                        <div className="flex gap-3 mt-1 text-xs text-gray-500">
                          <span>Técnica: {a.tecnica_avaliacao}</span>
                          <span>EPI eficaz: {a.epi_eficaz ? "✅ Sim" : "❌ Não"}</span>
                          {a.enquadramento_especial && <span className="text-red-600 font-bold">⭐ Atividade Especial</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* LTCAT */}
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <h3 className="text-xs font-bold text-gray-700 uppercase mb-3">IV — LTCAT de Referência</h3>
                {!pppDetalhe.ltcat?.titulo ? (
                  <p className="text-sm text-red-500">⚠️ LTCAT não encontrado</p>
                ) : (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="col-span-2"><p className="text-xs text-gray-500">Título</p><p className="font-medium">{pppDetalhe.ltcat?.titulo}</p></div>
                    <div><p className="text-xs text-gray-500">Data Emissão</p><p className="font-medium">{pppDetalhe.ltcat?.data_emissao}</p></div>
                    <div><p className="text-xs text-gray-500">Responsável</p><p className="font-medium">{pppDetalhe.ltcat?.responsavel}</p></div>
                  </div>
                )}
              </div>

              {/* Responsável Técnico */}
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <h3 className="text-xs font-bold text-gray-700 uppercase mb-3">V — Responsável Técnico</h3>
                {!pppDetalhe.responsavel_tecnico?.nome ? (
                  <p className="text-sm text-red-500">⚠️ Responsável técnico não informado</p>
                ) : (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><p className="text-xs text-gray-500">Nome</p><p className="font-medium">{pppDetalhe.responsavel_tecnico?.nome}</p></div>
                    <div><p className="text-xs text-gray-500">Registro</p><p className="font-medium font-mono">{pppDetalhe.responsavel_tecnico?.registro}</p></div>
                    <div><p className="text-xs text-gray-500">Função</p><p className="font-medium">{pppDetalhe.responsavel_tecnico?.funcao}</p></div>
                    <div><p className="text-xs text-gray-500">Conselho</p><p className="font-medium">{pppDetalhe.responsavel_tecnico?.conselho}</p></div>
                  </div>
                )}
              </div>

              {/* Resultado IA */}
              {resultadoIA && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-5">
                  <h3 className="text-xs font-bold text-purple-800 uppercase mb-3">🤖 Análise IA — Conformidade PPP</h3>
                  <div className="flex justify-between items-center mb-3">
                    <p className={`text-sm font-bold ${resultadoIA.apto_esocial ? "text-green-700" : "text-red-700"}`}>
                      {resultadoIA.apto_esocial ? "✅ Apto para eSocial" : "❌ Pendências para eSocial"}
                    </p>
                    <span className="text-lg font-black text-purple-700">
                      {Math.round((resultadoIA.score_conformidade || 0) * 100)}%
                    </span>
                  </div>
                  {resultadoIA.alertas?.length > 0 && (
                    <div className="space-y-1 mb-3">
                      {resultadoIA.alertas.map((a: string, i: number) => (
                        <p key={i} className="text-xs text-red-700">⚠️ {a}</p>
                      ))}
                    </div>
                  )}
                  {resultadoIA.recomendacoes?.length > 0 && (
                    <div className="space-y-1">
                      {resultadoIA.recomendacoes.map((r: string, i: number) => (
                        <p key={i} className="text-xs text-blue-700">💡 {r}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
