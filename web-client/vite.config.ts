import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: true, // Listen on all interfaces for iPad access
    port: 3000,
  },
  build: {
    outDir: 'dist',
  },
});

