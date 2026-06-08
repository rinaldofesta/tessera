/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0e1117",
        panel: "#161b26",
        panel2: "#1b2230",
        border: "#2a3343",
        muted: "#9aa7b8",
        ink: "#e6edf3",
        pass: "#22c55e",
        fail: "#ef4444",
        flaky: "#f59e0b",
        accent: "#2ecc71",
      },
    },
  },
  plugins: [],
};
