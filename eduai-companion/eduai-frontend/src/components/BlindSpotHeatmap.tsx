/**
 * Block C: Blind-Spot Heatmap — zeigt Fächer wo der Schüler
 * hohe Confidence hat aber falsch antwortet.
 */
interface BlindSpotFach {
  fach: string;
  blind_spots: number;
}

export function BlindSpotHeatmap({ fächer }: { fächer: BlindSpotFach[] }) {
  if (!fächer || fächer.length === 0) return null;

  return (
    <div
      className="rounded-2xl p-4"
      style={{
        background: "rgba(30,41,59,0.6)",
        border: "1px solid rgba(99,102,241,0.2)",
      }}
    >
      <div className="text-xs font-bold text-slate-300 mb-3">
        Blind Spots — du glaubst es zu wissen, liegst aber falsch
      </div>
      <div className="flex flex-wrap gap-2">
        {fächer.map((f) => (
          <div
            key={f.fach}
            className="px-2 py-1 rounded-lg text-xs font-medium"
            style={{
              background:
                f.blind_spots > 3
                  ? "rgba(239,68,68,0.25)"
                  : f.blind_spots > 1
                  ? "rgba(245,158,11,0.2)"
                  : "rgba(34,197,94,0.15)",
              color:
                f.blind_spots > 3
                  ? "#fca5a5"
                  : f.blind_spots > 1
                  ? "#fcd34d"
                  : "#86efac",
            }}
          >
            {f.fach}: {f.blind_spots}
          </div>
        ))}
      </div>
    </div>
  );
}

export default BlindSpotHeatmap;
