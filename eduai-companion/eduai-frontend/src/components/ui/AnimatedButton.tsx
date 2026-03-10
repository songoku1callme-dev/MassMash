import { motion } from "framer-motion";
import type { ReactNode, MouseEvent } from "react";

interface AnimatedButtonProps {
  children: ReactNode;
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void;
  className?: string;
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
  title?: string;
  style?: React.CSSProperties;
}

export default function AnimatedButton({
  children,
  onClick,
  className = "",
  disabled = false,
  type = "button",
  title,
  style,
}: AnimatedButtonProps) {
  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      type={type}
      title={title}
      style={style}
      whileHover={disabled ? undefined : { scale: 1.02, y: -1 }}
      whileTap={disabled ? undefined : { scale: 0.96 }}
      transition={{ type: "spring", stiffness: 600, damping: 25 }}
      className={`relative overflow-hidden ${className}`}
    >
      {children}
    </motion.button>
  );
}
