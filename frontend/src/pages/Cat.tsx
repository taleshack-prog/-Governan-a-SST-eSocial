// ==============================================================
// SST ESOCIAL GOV — Página: CAT (eSocial S-2210)
// Arquivo: frontend/src/pages/Cat.tsx
// ==============================================================

import { useCats } from "../hooks/useQueries";
import { Card, SectionTitle, Spinner, EmptyState, StatusBadge } from "../components/ui";

export function Cat() {
  const { data: cats = [], isLoading } = useCats();
  return (
    <div>
      <SectionTitle title="CAT — Comunicação de Acidente de Trabalho" subtitle="Registro de acidentes. Referência: eSocial S-2210 e CLT Art. 169." />
      <Card>
        {isLoading ? <div className="flex justify-center py-12"><Spinner /></div> :
          cats.length === 0 ? <EmptyState message="Nenhuma CAT registrada." /> : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Tipo</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Data do Acidente</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">CID</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">Afastamento</th>
                  <th className="text-left py-3 px-3 text-gray-500 font-medium">eSocial</th>
                </tr>
              </thead>
              <tbody>
                {cats.map((c: any) => (
                  <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-3 capitalize text-gray-700">{c.tipo_cat?.replace("_", " ")}</td>
                    <td className="py-3 px-3 text-gray-500">{new Date(c.data_acidente).toLocaleDateString("pt-BR")}</td>
                    <td className="py-3 px-3 font-mono text-xs text-gray-600">{c.cid_principal ?? "—"}</td>
                    <td className="py-3 px-3">{c.afastamento ? `${c.dias_afastamento ?? "?"} dias` : "Não"}</td>
                    <td className="py-3 px-3"><StatusBadge status={c.status_esocial} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </Card>
    </div>
  );
}
