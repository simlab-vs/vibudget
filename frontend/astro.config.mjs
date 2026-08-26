import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  server: { port: 4321 },
  vite: {
    server: {
      proxy: {
        "/api": {
          target: process.env.VIBUDGET_API_URL ?? "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  },
});
