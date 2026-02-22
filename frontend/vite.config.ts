import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/players": "http://127.0.0.1:8000",
      "/refresh": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/auth": "http://127.0.0.1:8000",
      "/squads": "http://127.0.0.1:8000",
      "/friends": "http://127.0.0.1:8000",
      "/admin/suggested": "http://127.0.0.1:8000",
      "/admin/users": "http://127.0.0.1:8000",
      "/admin/players": "http://127.0.0.1:8000",
      "/suggested": "http://127.0.0.1:8000",
    },
  },
});
