/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0F19",
        surface: "#131829",
        "surface-light": "#1C2333",
        "purple-accent": "#8A2BE2",
        "cyber-blue": "#00E5FF",
        "success-green": "#00FF7F",
        "danger-red": "#FF4757",
        "warning-yellow": "#FFD700",
        "text-primary": "#FFFFFF",
        "text-secondary": "#A0AEC0",
        "text-muted": "#4A5568",
      },
      fontFamily: {
        inter: ["Inter_400Regular"],
        "inter-medium": ["Inter_500Medium"],
        "inter-semibold": ["Inter_600SemiBold"],
        "inter-bold": ["Inter_700Bold"],
        poppins: ["Poppins_400Regular"],
        "poppins-medium": ["Poppins_500Medium"],
        "poppins-semibold": ["Poppins_600SemiBold"],
        "poppins-bold": ["Poppins_700Bold"],
      },
    },
  },
  plugins: [],
};
