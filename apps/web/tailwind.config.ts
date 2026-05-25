import type { Config } from 'tailwindcss';

// Rawasi Sama brand identity (SPEC §6).
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#253747',
          50: '#eef1f4',
          700: '#253747',
          900: '#1a2733',
        },
        gold: {
          DEFAULT: '#BD9B5E',
          400: '#cdb381',
          600: '#a8854a',
        },
      },
      fontFamily: {
        sans: ['var(--font-arabic)', 'Tahoma', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
