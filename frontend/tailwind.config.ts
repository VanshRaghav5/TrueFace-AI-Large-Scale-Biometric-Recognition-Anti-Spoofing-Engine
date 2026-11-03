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
        tf: {
          bg: "#F6F8FB",
          surface: "#FFFFFF",
          "surface-muted": "#EEF2F7",
          text: "#172033",
          "text-muted": "#5E6B7E",
          border: "#DCE3EC",
          primary: {
            DEFAULT: "#2457C5",
            hover: "#1D469F",
          },
          success: "#18794E",
          warning: "#9A5B00",
          danger: "#B42318",
          info: "#176B87",
        },
      },
      borderRadius: {
        card: "12px",
        input: "8px",
      },
    },
  },
  plugins: [],
};

export default config;

