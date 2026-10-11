import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Matches node_modules/<pkg>/ on both POSIX and Windows paths.
const inPackage = (id, pkg) => new RegExp(`[\\\\/]node_modules[\\\\/]${pkg}[\\\\/]`).test(id);

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/webhook': 'http://localhost:8000',
            '/api': 'http://localhost:8000',
        },
    },
    build: {
        rollupOptions: {
            output: {
                // Keep the big, rarely-changing libraries in their own files
                // so the browser can cache them separately from app code.
                manualChunks(id) {
                    if (inPackage(id, 'three')) return 'three';
                    if (inPackage(id, 'react') || inPackage(id, 'react-dom') || inPackage(id, 'scheduler')) return 'react';
                },
            },
        },
        // three.js alone is ~0.7 MB minified and cannot be made smaller. It is
        // loaded lazily (see Dashboard.jsx), off the critical path, so raise the
        // warning threshold just above it rather than ignore bigger regressions.
        chunkSizeWarningLimit: 800,
    },
});
