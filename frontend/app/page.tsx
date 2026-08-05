"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, ApiError, type ScoredJobOut, type ApplicationStats } from "@/lib/api";
import { JobCard } from "@/components/JobCard";
import { SummaryStrip } from "@/components/SummaryStrip";

export default function DashboardPage() {
  const [jobs, setJobs] = useState<ScoredJobOut[] | null>(null);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [minScore, setMinScore] = useState(0);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (score: number) => {
    setError(null);
    try {
      const [jobsRes, statsRes] = await Promise.all([api.listJobs(score), api.applicationStats()]);
      setJobs(jobsRes);
      setStats(statsRes);
      setNeedsProfile(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError("Unauthorized — check NEXT_PUBLIC_API_TOKEN in frontend/.env.local matches the backend's API_AUTH_TOKEN.");
      } else {
        setError(e instanceof Error ? e.message : "Failed to load jobs.");
      }
    }
  }, []);

  useEffect(() => {
    api.getProfile().catch((e) => {
      if (e instanceof ApiError && e.status === 404) setNeedsProfile(true);
    });
    load(minScore);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    setRefreshMessage(null);
    try {
      const result = await api.refreshJobs();
      setRefreshMessage(
        `Fetched ${result.fetched} postings (${result.new} new)${result.errors.length ? `, ${result.errors.length} source(s) had errors` : ""}.`
      );
      await load(minScore);
    } catch (e) {
      setRefreshMessage(e instanceof Error ? `Refresh failed: ${e.message}` : "Refresh failed.");
    } finally {
      setRefreshing(false);
    }
  }

  const topScore = jobs && jobs.length > 0 ? jobs[0].score.overall_score : null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-ink">Job Agent</h1>
          <p className="text-sm text-muted">Real listings, scored against your profile.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/profile" className="rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-base">
            Profile
          </Link>
          <button
            onClick={handleRefresh}
            disabled={refreshing || needsProfile}
            className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {refreshing ? "Refreshing…" : "Refresh jobs"}
          </button>
        </div>
      </header>

      {needsProfile && (
        <div className="mb-6 rounded-xl border border-warn bg-surface p-4 text-sm text-ink">
          No profile yet.{" "}
          <Link href="/profile" className="font-medium text-accent underline">
            Set up your profile
          </Link>{" "}
          before refreshing — matching needs something to match against.
        </div>
      )}

      {refreshMessage && <p className="mb-4 text-sm text-muted">{refreshMessage}</p>}
      {error && <p className="mb-4 text-sm text-bad">{error}</p>}

      <div className="mb-6">
        <SummaryStrip jobCount={jobs?.length ?? 0} topScore={topScore} stats={stats} />
      </div>

      <div className="mb-4 flex items-center gap-3">
        <label htmlFor="minScore" className="text-sm text-muted">
          Minimum match
        </label>
        <input
          id="minScore"
          type="range"
          min={0}
          max={100}
          step={5}
          value={minScore}
          onChange={(e) => {
            const v = Number(e.target.value);
            setMinScore(v);
            load(v);
          }}
          className="accent-accent"
        />
        <span className="font-mono text-sm text-ink">{minScore}%</span>
      </div>

      {jobs === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {jobs !== null && jobs.length === 0 && (
        <p className="rounded-xl border border-border bg-surface p-6 text-sm text-muted">
          No scored jobs yet. Click "Refresh jobs" to pull real postings from Greenhouse, Lever, Ashby, RemoteOK, and
          Himalayas and score them against your profile.
        </p>
      )}

      <div className="flex flex-col gap-3">
        {jobs?.map((sj, i) => (
          <JobCard key={sj.job.id} rank={i + 1} scoredJob={sj} />
        ))}
      </div>
    </main>
  );
}
