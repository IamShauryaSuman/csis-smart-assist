import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "bg-base": "#0D1117",
        "bg-surface": "#161B22",
        border: "#30363D",
        "text-primary": "#C9D1D9",
        "text-secondary": "#8B949E",
        success: "#3FB950",
        accent: "#80FC68",
        link: "#58A6FF",
        pending: "#D29922",
        danger: "#F85149",
      },
      fontFamily: {
        display: [
          "var(--font-space-grotesk)",
          "Space Grotesk",
          "Inter",
          "sans-serif",
        ],
        sans: ["var(--font-inter)", "Inter", "Roboto", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
