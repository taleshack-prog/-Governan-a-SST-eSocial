// RadarPrevi — controle de tema (padrão escuro, persistido)
export type Theme = "dark" | "light";

export function getTheme(): Theme {
  try { return (localStorage.getItem("rp_theme") as Theme) || "dark"; }
  catch { return "dark"; }
}
export function applyTheme(t: Theme) {
  document.documentElement.classList.toggle("dark", t === "dark");
  try { localStorage.setItem("rp_theme", t); } catch {}
}
export function toggleTheme(): Theme {
  const next: Theme = document.documentElement.classList.contains("dark") ? "light" : "dark";
  applyTheme(next);
  return next;
}
