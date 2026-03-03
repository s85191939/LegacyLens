/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        terminal: ['VT323', 'Share Tech Mono', 'monospace'],
      },
      colors: {
        crt: {
          bg: '#0a0e0a',
          green: '#33ff33',
          dim: '#1a331a',
          border: '#2d4a2d',
        },
      },
    },
  },
  plugins: [],
}
