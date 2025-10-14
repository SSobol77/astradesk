// services/admin-portal/tailwind.config.ts

import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", ...defaultTheme.fontFamily.sans],
      },
      colors: {
        astral: {
          50: "#f5f8ff",
          100: "#e6eeff",
          200: "#c2d5ff",
          300: "#9cbaff",
          400: "#769aff",
          500: "#4a74ff",
          600: "#3657db",
          700: "#283fb7",
          800: "#1d2d93",
          900: "#121f70",
        },
        slate: {
          950: "#0b1220",
        },
        border: "#d6deff",
        surface: "#ffffff",
      },
      boxShadow: {
        card: "0 12px 32px -16px rgba(15, 23, 42, 0.35)",
        subtle: "0 8px 20px -12px rgba(15, 23, 42, 0.25)",
      },
    },
  },
  plugins: [
    ({ addVariant }) => {
      // Adds a focus-visible within variant to ensure keyboard accessibility styles.
      addVariant("focus-within-visible", "&:focus-within-visible");
    },
  ],
};

export default config;
