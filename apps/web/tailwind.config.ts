import type { Config } from 'tailwindcss';

// هوية رواسي سما البصرية
const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#253747',
          50: '#f4f6f8',
          700: '#2d4357',
          900: '#1a2730',
        },
        gold: {
          DEFAULT: '#BD9B5E',
          light: '#d4bb8a',
        },
      },
      fontFamily: {
        sans: ['var(--font-arabic)', 'system-ui', 'Segoe UI', 'Tahoma', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
