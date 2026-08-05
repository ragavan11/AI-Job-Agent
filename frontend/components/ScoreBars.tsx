const TIERS = [
  { min: 80, color: "bg-good" },
  { min: 55, color: "bg-warn" },
  { min: 0, color: "bg-bad" },
];

function colorFor(score: number): string {
  return TIERS.find((t) => score >= t.min)?.color ?? "bg-bad";
}

export function ScoreBars({ score }: { score: number }) {
  const filled = Math.round((score / 100) * 5);
  const color = colorFor(score);
  const heights = [6, 10, 14, 18, 22]; // px, ascending like a signal-strength icon

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="flex items-end gap-[3px]" aria-hidden>
        {heights.map((h, i) => (
          <div
            key={i}
            style={{ height: `${h}px` }}
            className={`w-[5px] rounded-sm ${i < filled ? color : "bg-border"}`}
          />
        ))}
      </div>
      <span className="font-mono text-sm font-semibold text-ink tabular-nums">{Math.round(score)}%</span>
    </div>
  );
}
