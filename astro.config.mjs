import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  output: 'static',
  site: 'https://blue-ocean-marketing.github.io',
  devToolbar: { enabled: false },
  vite: {
    plugins: [tailwindcss()]
  }
});
