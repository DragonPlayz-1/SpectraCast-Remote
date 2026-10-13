import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: '../src/spectracast/web/dist',
    emptyOutDir: true,
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
});
