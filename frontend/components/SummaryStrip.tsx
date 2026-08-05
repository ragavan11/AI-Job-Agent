import type { ApplicationStats } from "@/lib/api";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-2xl font-semibold text-ink tabular-nums">{value}</span>
      <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
    </div>
  );
}

export function SummaryStrip({
  jobCount,
  topScore,
  stats,
}: {
  jobCount: number;
  topScore: number | null;
  stats: ApplicationStats | null;
}) {
  return (
    <div className="flex flex-wrap gap-8 rounded-xl border border-border bg-surface p-6 shadow-sm">
      <Stat label="Jobs in range" value={jobCount} />
      <Stat label="Top match" value={topScore !== null ? `${Math.round(topScore)}%` : "—"} />
      <Stat label="Applied" value={stats?.counts.applied ?? 0} />
      <Stat label="Interviewing" value={stats?.counts.interviewing ?? 0} />
      <Stat label="Response rate" value={stats ? `${stats.response_rate}%` : "—"} />
    </div>
  );
}
