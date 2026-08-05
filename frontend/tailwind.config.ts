import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#F1F3F5",       // cool slate-mist background, not warm cream
        surface: "#FFFFFF",
        border: "#DCE1E6",
        ink: "#14181F",
        muted: "#5B6472",
        accent: "#1F6F78",     // deep teal — the app's one confident color
        "accent-soft": "#E3EFEF",
        good: "#2F9E62",
        warn: "#D89A2A",
        bad: "#C24B3F",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        body: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
