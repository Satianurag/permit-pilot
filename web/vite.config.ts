import { resolve } from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "clerk-spa-fallback",
      configureServer(server) {
        server.middlewares.use((req, _res, next) => {
          const path = req.url?.split("?")[0] ?? "";
          if (
            path === "/login" ||
            path === "/dashboard" ||
            path === "/activity" ||
            path === "/tasks" ||
            path === "/permits" ||
            path === "/agents" ||
            path === "/governance" ||
            path === "/memory" ||
            path === "/traces" ||
            path.startsWith("/cases/")
          ) {
            req.url = "/app.html";
          }
          next();
        });
      },
    },
  ],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        app: resolve(__dirname, "app.html"),
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
