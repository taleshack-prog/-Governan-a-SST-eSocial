// ==============================================================
// SST ESOCIAL GOV — App.tsx
// Arquivo: frontend/src/App.tsx
// ==============================================================

import PrevIA from "./components/PrevIA";
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { router } from "./router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,   // 2 minutos
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: { fontSize: "14px" },
        }}
      />
    </QueryClientProvider>
  );
}
