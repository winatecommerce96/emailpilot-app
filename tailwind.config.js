/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./frontend/public/**/*.{html,js,jsx,ts,tsx}",
    "./frontend/public/components/**/*.{js,jsx,ts,tsx}",
    "./frontend/public/dist/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'ep-blue': '#3369DC',
        'ep-purple': '#8A6CF7',
        'ep-lime': '#C5FF75',
        'ep-black': '#000000',
        'ep-white': '#FFFFFF',
      },
      fontFamily: {
        'heading': ['Red Hat Display', 'ui-sans-serif', 'system-ui'],
        'body': ['Poppins', 'ui-sans-serif', 'system-ui'],
      }
    },
  },
  darkMode: ['class', '[data-theme="dark"]'],
  plugins: [],
}