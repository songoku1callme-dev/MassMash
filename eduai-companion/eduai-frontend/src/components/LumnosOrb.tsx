import { motion, useAnimation, useMotionValue,
         useSpring, useTransform } from "framer-motion";
import { useEffect, useRef } from "react";

// Fach → Orb-Farbe
const FACH_FARBEN: Record<string, [string, string]> = {
  "Mathematik": ["#3b82f6", "#06b6d4"],   // Neon-Blau
  "Physik":     ["#06b6d4", "#0891b2"],   // Cyan
  "Chemie":     ["#10b981", "#059669"],   // Grün
  "Biologie":   ["#22c55e", "#16a34a"],   // Gift-Grün
  "Geschichte": ["#f59e0b", "#d97706"],   // Gold
  "Deutsch":    ["#ec4899", "#db2777"],   // Pink
  "Englisch":   ["#f97316", "#ea580c"],   // Orange
  "Informatik": ["#6366f1", "#4f46e5"],   // Indigo
  "Latein":     ["#a78bfa", "#7c3aed"],   // Violett
  "Musik":      ["#f43f5e", "#e11d48"],   // Rot
  "default":    ["#6366f1", "#8b5cf6"],
};

interface OrbProps {
  fach?: string;
  isTyping?: boolean;
  isListening?: boolean;
  isLearning?: boolean;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
}

export default function LumnosOrb({
  fach = "default",
  isTyping = false,
  isListening = false,
  isLearning = false,
  size = "md",
  onClick,
}: OrbProps) {
  const controls   = useAnimation();
  // Gold override when learning from internet
  const goldFarben: [string, string] = ["#f59e0b", "#f97316"];
  const [c1, c2]   = isLearning ? goldFarben : (FACH_FARBEN[fach] ?? FACH_FARBEN["default"]);
  const mouseX     = useMotionValue(0);
  const mouseY     = useMotionValue(0);
  const springX    = useSpring(mouseX, { stiffness: 80, damping: 20 });
  const springY    = useSpring(mouseY, { stiffness: 80, damping: 20 });
  const rotateX    = useTransform(springY, [-50, 50], [15, -15]);
  const rotateY    = useTransform(springX, [-50, 50], [-15, 15]);
  const orbRef     = useRef<HTMLDivElement>(null);

  const SIZES = { sm: 48, md: 80, lg: 140 };
  const px = SIZES[size];

  // Maus-Tilt
  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = orbRef.current?.getBoundingClientRect();
    if (!rect) return;
    mouseX.set(e.clientX - rect.left - rect.width  / 2);
    mouseY.set(e.clientY - rect.top  - rect.height / 2);
  };
  const handleMouseLeave = () => { mouseX.set(0); mouseY.set(0); };

  // Animationen
  useEffect(() => {
    if (isLearning) {
      controls.start({
        scale: [1, 1.15, 1, 1.1, 1],
        rotate: [0, 5, -5, 0],
        transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
      });
    } else if (isListening) {
      controls.start({
        scale: [1, 1.25, 1, 1.2, 1],
        transition: { duration: 0.8, repeat: Infinity }
      });
    } else if (isTyping) {
      controls.start({
        scale: [1, 1.08, 1],
        transition: { duration: 0.6, repeat: Infinity, ease: "easeInOut" }
      });
    } else {
      controls.start({
        scale: [1, 1.04, 1],
        transition: { duration: 3, repeat: Infinity, ease: "easeInOut" }
      });
    }
  }, [isTyping, isListening, isLearning, controls]);

  return (
    <motion.div
      ref={orbRef}
      style={{ width: px, height: px, rotateX, rotateY,
               transformStyle: "preserve-3d", cursor: onClick ? "pointer" : "default" }}
      animate={controls}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      whileHover={{ scale: 1.06 }}
      whileTap={{ scale: 0.95 }}>

      {/* Äußerer Glow-Ring */}
      <div style={{
        position: "absolute", inset: -px * 0.15,
        borderRadius: "50%",
        background: `radial-gradient(circle, ${c1}22 0%, transparent 70%)`,
        animation: "pulse 2s ease-in-out infinite",
      }} />

      {/* Haupt-Orb */}
      <div style={{
        width: "100%", height: "100%",
        borderRadius: "50%",
        background: `radial-gradient(circle at 35% 35%, ${c1}, ${c2} 60%, #0a0f1e)`,
        boxShadow: `0 0 ${px * 0.3}px ${c1}88,
                    0 0 ${px * 0.6}px ${c1}44,
                    inset 0 0 ${px * 0.2}px rgba(255,255,255,0.15)`,
        display: "flex", alignItems: "center",
        justifyContent: "center",
        position: "relative", overflow: "hidden",
      }}>
        {/* Glanz-Highlight */}
        <div style={{
          position: "absolute", top: "12%", left: "18%",
          width: "35%", height: "25%",
          background: "radial-gradient(ellipse, rgba(255,255,255,0.4), transparent)",
          borderRadius: "50%",
          transform: "rotate(-30deg)",
        }} />

        {/* \u2726 Symbol */}
        <span style={{
          color: "rgba(255,255,255,0.95)",
          fontSize: px * 0.38,
          fontWeight: 900,
          textShadow: `0 0 ${px * 0.15}px rgba(255,255,255,0.8)`,
          zIndex: 1, userSelect: "none",
        }}>{"\u2726"}</span>

        {/* Tipp-Wellen */}
        {isTyping && [0, 1, 2].map(i => (
          <motion.div key={i} style={{
            position: "absolute", inset: 0,
            borderRadius: "50%",
            border: `2px solid ${c1}`,
            opacity: 0,
          }} animate={{
            scale:   [1, 1.8 + i * 0.3],
            opacity: [0.6, 0],
          }} transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: i * 0.3,
            ease: "easeOut",
          }} />
        ))}

        {/* Hör-Partikel */}
        {isListening && [...Array(6)].map((_, i) => (
          <motion.div key={i} style={{
            position: "absolute",
            width: 4, height: 4,
            borderRadius: "50%",
            background: "rgba(255,255,255,0.9)",
          }} animate={{
            x: [0, Math.cos(i * 60 * Math.PI / 180) * px * 0.5],
            y: [0, Math.sin(i * 60 * Math.PI / 180) * px * 0.5],
            opacity: [1, 0],
            scale: [1, 0],
          }} transition={{
            duration: 0.8, repeat: Infinity,
            delay: i * 0.13, ease: "easeOut",
          }} />
        ))}

        {/* Gold-Ring Animation (Learning) */}
        {isLearning && [0, 1].map(i => (
          <motion.div key={`gold-${i}`} style={{
            position: "absolute", inset: 0,
            borderRadius: "50%",
            border: "2px solid #f59e0b",
            opacity: 0,
          }} animate={{
            scale: [1, 2.5],
            opacity: [0.8, 0],
          }} transition={{
            duration: 1.5,
            repeat: Infinity,
            delay: i * 0.7,
            ease: "easeOut",
          }} />
        ))}
      </div>
    </motion.div>
  );
}
