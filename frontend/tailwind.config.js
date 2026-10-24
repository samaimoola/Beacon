/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'ohio-scarlet': '#BB0000',
        'ohio-grey': '#666666',
        'ohio-light': '#F5F5F5',
        'ohio-dark': '#2C2C2C',
      },
    },
  },
  plugins: [],
};
