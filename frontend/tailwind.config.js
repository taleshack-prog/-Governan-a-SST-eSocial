/** ==============================================================
 * RadarPrevi — Tailwind Config (tema por tokens + dark default)
 * ============================================================== */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Libre Franklin", "system-ui", "-apple-system", "sans-serif"],
        serif: ["Newsreader", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      colors: {
        // superfícies / texto (novos tokens semânticos — flipam com o tema)
        canvas:  "rgb(var(--c-bg) / <alpha-value>)",
        surface: "rgb(var(--c-surface) / <alpha-value>)",
        panel:   "rgb(var(--c-panel) / <alpha-value>)",
        ink:     "rgb(var(--c-ink) / <alpha-value>)",
        ink2:    "rgb(var(--c-ink2) / <alpha-value>)",
        muted:   "rgb(var(--c-muted) / <alpha-value>)",
        faint:   "rgb(var(--c-faint) / <alpha-value>)",
        line:    "rgb(var(--c-line) / <alpha-value>)",
        line2:   "rgb(var(--c-line2) / <alpha-value>)",
        // marca (teal) — substitui o indigo antigo
        brand: {
          50:  "rgb(var(--c-brand-50) / <alpha-value>)",
          100: "rgb(var(--c-brand-100) / <alpha-value>)",
          500: "rgb(var(--c-brand-500) / <alpha-value>)",
          600: "rgb(var(--c-brand-600) / <alpha-value>)",
          700: "rgb(var(--c-brand-700) / <alpha-value>)",
        },
        credit: "rgb(var(--c-credit) / <alpha-value>)",
        risk:   "rgb(var(--c-risk) / <alpha-value>)",
        sidebar: {
          DEFAULT: "rgb(var(--c-sidebar) / <alpha-value>)",
          ink:     "rgb(var(--c-sidebar-ink) / <alpha-value>)",
          muted:   "rgb(var(--c-sidebar-muted) / <alpha-value>)",
        },
      },
    },
  },
  plugins: [],
};
