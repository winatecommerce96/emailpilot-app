import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  root: 'frontend',
  plugins: [],
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@features': path.resolve(__dirname, './src/features'),
      '@auth': path.resolve(__dirname, './src/auth'),
      '@debug': path.resolve(__dirname, './src/debug'),
      '@services': path.resolve(__dirname, './src/services'),
    }
  },
  
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
    manifest: true,
    rollupOptions: {
      input: {
        'index': path.resolve(__dirname, 'frontend/src/entries/index.ts'),
        'clients': path.resolve(__dirname, 'frontend/src/entries/clients.ts'),
        'calendar': path.resolve(__dirname, 'frontend/src/entries/calendar.ts'),
        'reports': path.resolve(__dirname, 'frontend/src/entries/reports.ts'),
        'settings': path.resolve(__dirname, 'frontend/src/entries/settings.ts'),
        'admin': path.resolve(__dirname, 'frontend/src/entries/admin.ts'),
      },
    },
  },
  
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
