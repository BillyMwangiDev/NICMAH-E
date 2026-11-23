/** Tailwind is compiled once at build time (npm run build:css) into
 *  core/static/css/tailwind.css. The server never needs Node. */
module.exports = {
  content: [
    "./core/templates/**/*.html",
    "./*/templates/**/*.html",
    "./core/static/js/*.js",
  ],
  safelist: [
    // Classes assembled in JavaScript template literals (see sale_create.html, main.js).
    { pattern: /^(bg|text|border)-(green|red|yellow|blue|gray|purple|orange|amber|emerald|sky)-(50|100|200|300|400|500|600|700|800|900)$/ },
    { pattern: /^(opacity|translate-y|scale)-/ },
    "hidden", "active", "show", "open", "line-clamp-2", "line-clamp-3",
  ],
  theme: {
    extend: {
      colors: {
        "agro-green": "#16a34a",
        "agro-dark": "#14532d",
        "agro-light": "#bbf7d0",
        "agro-brown": "#92400e",
        "agro-gold": "#f59e0b",
        "agro-sky": "#0ea5e9",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        display: ["Poppins", "sans-serif"],
      },
    },
  },
  plugins: [],
};
