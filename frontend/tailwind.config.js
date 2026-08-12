/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        flame: {
          DEFAULT: 'rgb(217, 64, 24)', // #d94018
          light: 'rgb(237, 96, 52)',
          dark: 'rgb(181, 46, 12)',
        },
        ember: {
          DEFAULT: 'rgb(255, 170, 0)', // #ffaa00
          light: 'rgb(255, 194, 61)',
          dark: 'rgb(224, 145, 0)',
        },
      },
    },
  },
  plugins: [],
}
