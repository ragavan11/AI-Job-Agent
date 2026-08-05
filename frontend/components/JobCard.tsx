"use client";

import { useState } from "react";
import type { ScoredJobOut } from "@/lib/api";
import { api } from "@/lib/api";
import { ScoreBars } from "./ScoreBars";

function formatSalary(min: number | null, max: number | null, currency: string | null): string | null {
  if (!min && !max) return null;
  const fmt = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`);
  const c = currency || "";
  if (min && max) return `${c} ${fmt(min)}–${fmt(max)}`;
  return `${c} ${fmt((min || max) as number)}+`;
}

export function JobCard({ rank, scoredJob }: { rank: number; scoredJob: ScoredJobOut }) {
  const { job, score } = scoredJob;
  const [busy, setBusy] = useState<"resume" | "letter" | "save" | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency);

  async function handle(action: "resume" | "letter" | "save") {
    setBusy(action);
    setMessage(null);
    try {
      if (action === "resume") {
        await api.tailorResume(job.id);
        setMessage("Tailored resume created — see the Resumes list.");
      } else if (action === "letter") {
        await api.generateCoverLetter(job.id);
        setMessage("Cover letter generated.");
      } else {
        await api.saveApplication(job.id);
        setMessage("Saved to your tracker.");
      }
    } catch (e) {
      setMessage(e instanceof Error ? `Failed: ${e.message}` : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex gap-4 rounded-xl border border-border bg-surface p-5 shadow-sm">
      <div className="w-8 shrink-0 pt-1 text-right font-mono text-sm text-muted">
        {String(rank).padStart(2, "0")}
      </div>

      <div className="w-16 shrink-0">
        <ScoreBars score={score.overall_score} />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="truncate font-display text-lg font-medium text-ink">{job.title}</h3>
          <span className="shrink-0 text-xs uppercase tracking-wide text-muted">{job.source}</span>
        </div>
        <p className="text-sm text-muted">
          {job.company} · {job.location || (job.remote ? "Remote" : "")}
          {salary ? ` · ${salary}` : ""}
        </p>

        {job.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {job.tags.slice(0, 8).map((tag) => (
              <span
                key={tag}
                className={`rounded-full px-2 py-0.5 text-xs ${
                  score.matched_skills.includes(tag) ? "bg-accent-soft text-accent" : "bg-base text-muted"
                }`}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <a
            href={job.apply_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-ink hover:bg-base"
          >
            View posting ↗
          </a>
          <button
            onClick={() => handle("resume")}
            disabled={busy !== null}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {busy === "resume" ? "Tailoring…" : "Tailor resume"}
          </button>
          <button
            onClick={() => handle("letter")}
            disabled={busy !== null}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {busy === "letter" ? "Writing…" : "Cover letter"}
          </button>
          <button
            onClick={() => handle("save")}
            disabled={busy !== null}
            className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-ink hover:bg-base disabled:opacity-50"
          >
            {busy === "save" ? "Saving…" : "Track"}
          </button>
          {message && <span className="text-xs text-muted">{message}</span>}
        </div>
      </div>
    </div>
  );
}
