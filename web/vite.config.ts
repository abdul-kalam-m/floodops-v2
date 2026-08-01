import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Static SPA served at site root on Cloudflare Pages (a separate project from v1's).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { target: "es2020", sourcemap: false },
});
