export function LoadingDots() {
  return (
    <div className="flex gap-3 px-4 py-4 bg-zinc-900/60">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-emerald-600">
        <span className="text-xs">AI</span>
      </div>
      <div className="flex items-center gap-1 pt-2">
        <div className="w-2 h-2 bg-zinc-500 rounded-full loading-dot" />
        <div className="w-2 h-2 bg-zinc-500 rounded-full loading-dot" />
        <div className="w-2 h-2 bg-zinc-500 rounded-full loading-dot" />
      </div>
    </div>
  );
}
