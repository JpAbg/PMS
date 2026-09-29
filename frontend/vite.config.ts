import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { VitePWA } from 'vite-plugin-pwa';
import proxyOptions from './proxyOptions.js';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  base: mode === 'capacitor'
    ? './'
    : '/assets/pms/frontend/',

  plugins: [
    vue(),

    VitePWA({
      registerType: 'autoUpdate',

      manifest: {
        name: 'Pomas',
        short_name: 'Pomas',
        description: 'Pomas project management workspace',
        id: '/pms',
        start_url: '/pms',
        scope: '/pms',
        lang: 'en',
        display: 'standalone',
        orientation: 'any',
        // Chrome reads these manifest assets for the install surface. Use the
        // transparent source logo directly; generated pwa-* images contained
        // a legacy dark square background.
        theme_color: '#257804',
        background_color: '#ffffff',
        categories: ['productivity', 'business'],

        icons: [
          {
            src: 'Pomas-Logo.png',
            sizes: '1103x1426',
            type: 'image/png',
            purpose: 'any',
          },
        ],
        screenshots: [
          {
            src: 'apps/pms/frontend/public/pomas-board-desktop.png',
            src: 'pomas-board-desktop.png',
            type: 'image/png',
            form_factor: 'wide',
            label: 'Pomas project board',
          },
        ],
      },

      workbox: {
        navigateFallback: null,
      },
    }),
  ],

  server: {
    port: 8080,
    host: '0.0.0.0',
    proxy: proxyOptions,
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },

  build: {
    outDir: mode === 'capacitor'
      ? './dist'
      : '../pms/public/frontend',

    emptyOutDir: true,
    target: 'es2015',
  },
}));
