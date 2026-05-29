// ==============================================================
// SST ESOCIAL GOV — Página: Exames Médicos (S-2220)
// Arquivo: frontend/src/pages/ExamesMedicos.tsx
// ==============================================================

import { useExames } from "../hooks/useQueries";
import { Card, SectionTitle, Spinner, EmptyState, StatusBadge } from "../components/ui";

export function ExamesMedicos() {
  const { data: exames = [], isLoading } = useExames();

  return (
    <div>
      <SectionTitle title="Exames Médicos — ASO / PCMSO" subtitle="Monitoramento da saúde ocupacional. Referência: NR-07 e eSocial S-2220." />
      <Card>
        {isLoading ? <div className="flex justify-center py-12"><Spinner /></div> :
          exames.length === 0 ? <EmptyState message="Nenhum exame médico registrado." /> : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Trabalhador</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Tipo</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Data</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Resultado</th>
                </tr>
              </thead>
              <tbody>
                {exames.map((e: any) => (
                  <tr key={e.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-3 text-gray-700 font-mono text-xs">{e.trabalhador_id?.slice(0, 8)}…</td>
                    <td className="py-3 px-3 capitalize text-gray-700">{e.tipo_exame?.replace("_", " ")}</td>
                    <td className="py-3 px-3 text-gray-500">{e.data_exame}</td>
                    <td className="py-3 px-3">{e.resultado ? <StatusBadge status={e.resultado} /> : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </Card>
    </div>
  );
}
