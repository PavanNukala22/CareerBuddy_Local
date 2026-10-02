/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './*/templates/**/*.html',
    './static/**/*.html',
    './*/static/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        coral: "#ff4d6d",
        "coral-hover": "#ff3355",
      },
      fontFamily: {
        serif: ["Newsreader", "serif"],
        sans: ["Outfit", "sans-serif"],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries'),
  ],
}
