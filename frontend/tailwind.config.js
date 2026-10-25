/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        storm: {
          950: '#08191d',
          900: '#0d2429',
          800: '#123137',
          700: '#1a4047',
          600: '#24545a',
          500: '#336a6e',
        },
        ivory: { DEFAULT: '#f6f1e6', 50: '#fbf8f1', 200: '#ece4d2', 300: '#dcd1ba' },
        ink: { DEFAULT: '#1b2829', soft: '#46534f', faint: '#5c6761' },
        seaglass: { DEFAULT: '#8fb9a8', deep: '#3d6d60', pale: '#d7e8df' },
        mist: { DEFAULT: '#bfe3e6', deep: '#7fc0c7' },
        lamp: { DEFAULT: '#f2b45a', deep: '#8a520c', pale: '#fbe9c9' },
        coral: { DEFAULT: '#e0735f', deep: '#a8432f', pale: '#f8ddd5' },
      },
      fontFamily: {
        display: ['var(--font-display)', 'Georgia', 'serif'],
        sans: ['var(--font-ui)', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
