/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			lumnos: {
  				bg:        "var(--lumnos-bg)",
  				surface:   "var(--lumnos-surface)",
  				card:      "var(--lumnos-card)",
  				border:    "var(--lumnos-border)",
  				glow:      "#6366f1",
  				"glow-2":  "#8b5cf6",
  				"glow-3":  "#06b6d4",
  				text:      "var(--lumnos-text)",
  				muted:     "var(--lumnos-muted)",
  			}
  		},
  		backgroundImage: {
  			"lumnos-gradient": "linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #06b6d4 100%)",
  			"lumnos-card": "linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.05) 100%)",
  			"cyber-grid": "linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px)",
  		},
  		backgroundSize: {
  			"cyber-grid": "32px 32px",
  		},
  		boxShadow: {
  			"glow-sm":  "0 0 10px rgba(99,102,241,0.4)",
  			"glow-md":  "0 0 20px rgba(99,102,241,0.5)",
  			"glow-lg":  "0 0 40px rgba(99,102,241,0.6)",
  			"glow-cyan": "0 0 20px rgba(6,182,212,0.5)",
  		},
  		animation: {
  			"pulse-glow": "pulse-glow 2s ease-in-out infinite",
  			"float":      "float 3s ease-in-out infinite",
  			"shimmer":    "shimmer 2s linear infinite",
  			"slide-up":   "slide-up 0.3s ease-out",
  			"fade-in":    "fade-in 0.4s ease-out",
  		},
  		keyframes: {
  			"pulse-glow": {
  				"0%, 100%": { boxShadow: "0 0 15px rgba(99,102,241,0.4)" },
  				"50%":      { boxShadow: "0 0 30px rgba(99,102,241,0.8)" }
  			},
  			"float": {
  				"0%, 100%": { transform: "translateY(0px)" },
  				"50%":      { transform: "translateY(-6px)" }
  			},
  			"shimmer": {
  				"0%":   { backgroundPosition: "-1000px 0" },
  				"100%": { backgroundPosition: "1000px 0" }
  			},
  			"slide-up": {
  				"from": { opacity: "0", transform: "translateY(10px)" },
  				"to":   { opacity: "1", transform: "translateY(0)" }
  			},
  			"fade-in": {
  				"from": { opacity: "0" },
  				"to":   { opacity: "1" }
  			}
  		},
  	}
  },
  plugins: [import("tailwindcss-animate")],
}

