import { motion, useMotionValue, useSpring,
         useTransform } from "framer-motion";
import { useRef } from "react";

interface BentoTileProps {
  children:  React.ReactNode;
  col?:      number;
  row?:      number;
  color?:    string;
  onClick?:  () => void;
  glow?:     boolean;
  delay?:    number;
}

export default function BentoTile({
  children, col = 1, row = 1,
  color = "#6366f1", onClick,
  glow = false, delay = 0,
}: BentoTileProps) {
  const ref    = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springX  = useSpring(mouseX, { stiffness: 120, damping: 25 });
  const springY  = useSpring(mouseY, { stiffness: 120, damping: 25 });
  const rotateX  = useTransform(springY, [-60, 60], [6, -6]);
  const rotateY  = useTransform(springX, [-60, 60], [-6, 6]);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    mouseX.set(e.clientX - rect.left - rect.width  / 2);
    mouseY.set(e.clientY - rect.top  - rect.height / 2);
  };
  const reset = () => { mouseX.set(0); mouseY.set(0); };

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: "easeOut" }}
      style={{
        gridColumn:    `span ${col}`,
        gridRow:       `span ${row}`,
        rotateX, rotateY,
        transformStyle: "preserve-3d",
        perspective:   "800px",
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={reset}
      whileHover={{ scale: 1.02, zIndex: 10 }}
      whileTap={onClick ? { scale: 0.98 } : {}}
      onClick={onClick}
      className={onClick ? "cursor-pointer" : ""}
    >
      <div style={{
        height:        "100%",
        borderRadius:  "20px",
        background:    `${color}14`,
        border:        `1px solid ${color}40`,
        backdropFilter: "blur(16px)",
        boxShadow:     glow
          ? `0 0 30px ${color}30, inset 0 0 20px ${color}08`
          : "none",
        overflow:      "hidden",
        transition:    "box-shadow 0.3s ease",
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.boxShadow =
          `0 0 40px ${color}50, inset 0 0 25px ${color}12`;
        (e.currentTarget as HTMLDivElement).style.borderColor =
          `${color}80`;
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.boxShadow =
          glow ? `0 0 30px ${color}30` : "none";
        (e.currentTarget as HTMLDivElement).style.borderColor =
          `${color}40`;
      }}>
        {children}
      </div>
    </motion.div>
  );
}
