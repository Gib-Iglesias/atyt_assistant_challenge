import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, proxya al backend. En produccion es nginx quien enruta.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/auth": "http://localhost:8000",
      "/api": "http://localhost:8001",
    },
  },
});
