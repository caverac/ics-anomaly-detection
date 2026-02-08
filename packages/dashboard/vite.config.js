import path from 'path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src')
        }
    },
    server: {
        port: 3090,
        strictPort: true,
        proxy: {
            '/api': {
                target: 'http://localhost:8084',
                changeOrigin: true,
                rewrite: function (path) { return path.replace(/^\/api/, ''); }
            }
        }
    },
    preview: {
        port: 3090
    }
});
