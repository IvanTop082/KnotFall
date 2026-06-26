import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        breach: {
          black: "#07090f",
          panel: "#10141f",
          line: "#263244",
          red: "#ef4444",
          orange: "#f97316",
          purple: "#8b5cf6",
          green: "#22c55e",
        },
      },
    },
  },
  plugins: [],
};

export default config;
