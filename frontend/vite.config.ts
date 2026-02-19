import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/players": "http://127.0.0.1:8000",
      "/refresh": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
