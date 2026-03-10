import { motion, AnimatePresence } from "framer-motion";
import { toastVariants } from "../../lib/animations";
import { useEffect } from "react";

export interface ToastData {
  id: string;
  icon: string;
  title: string;
  message: string;
}

interface ToastProps {
  toast: ToastData | null;
  onDismiss: () => void;
  duration?: number;
}

export default function Toast({ toast, onDismiss, duration = 3500 }: ToastProps) {
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(onDismiss, duration);
    return () => clearTimeout(timer);
  }, [toast, onDismiss, duration]);

  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          key={toast.id}
          variants={toastVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          className="fixed top-6 right-6 z-[100] bg-slate-800/90 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-2xl shadow-black/40 flex items-center gap-3 min-w-[16rem] cursor-pointer"
          onClick={onDismiss}
        >
          <motion.span
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.15, type: "spring", stiffness: 500 }}
            className="text-2xl"
          >
            {toast.icon}
          </motion.span>
          <div>
            <p className="text-white font-semibold text-sm">{toast.title}</p>
            <p className="text-slate-400 text-xs">{toast.message}</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
