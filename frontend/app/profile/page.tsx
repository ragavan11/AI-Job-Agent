"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, type ProfileOut } from "@/lib/api";

type FormState = {
  full_name: string;
  email: string;
  phone: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  location: string;
  skills: string; // comma-separated in the form, array on the wire
  experience_years: string;
  preferred_locations: string; // comma-separated
  remote_ok: boolean;
  min_salary: string;
  work_authorization: string;
  notice_period_days: string;
};

const EMPTY: FormState = {
  full_name: "", email: "", phone: "", linkedin_url: "", github_url: "", portfolio_url: "",
  location: "", skills: "", experience_years: "0", preferred_locations: "",
  remote_ok: true, min_salary: "", work_authorization: "", notice_period_days: "",
};

function toForm(p: ProfileOut): FormState {
  return {
    full_name: p.full_name, email: p.email, phone: p.phone || "",
    linkedin_url: p.linkedin_url || "", github_url: p.github_url || "", portfolio_url: p.portfolio_url || "",
    location: p.location || "", skills: p.skills.join(", "), experience_years: String(p.experience_years),
    preferred_locations: p.preferred_locations.join(", "), remote_ok: p.remote_ok,
    min_salary: p.min_salary != null ? String(p.min_salary) : "",
    work_authorization: p.work_authorization || "", notice_period_days: p.notice_period_days != null ? String(p.notice_period_days) : "",
  };
}

export default function ProfilePage() {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api
      .getProfile()
      .then((p) => setForm(toForm(p)))
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 404)) {
          setMessage(e instanceof Error ? e.message : "Failed to load profile.");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await api.saveProfile({
        full_name: form.full_name,
        email: form.email,
        phone: form.phone || null,
        linkedin_url: form.linkedin_url || null,
        github_url: form.github_url || null,
        portfolio_url: form.portfolio_url || null,
        location: form.location || null,
        skills: form.skills.split(",").map((s) => s.trim()).filter(Boolean),
        experience_years: Number(form.experience_years) || 0,
        preferred_locations: form.preferred_locations.split(",").map((s) => s.trim()).filter(Boolean),
        remote_ok: form.remote_ok,
        min_salary: form.min_salary ? Number(form.min_salary) : null,
        work_authorization: form.work_authorization || null,
        notice_period_days: form.notice_period_days ? Number(form.notice_period_days) : null,
        education: [],
        certificates: [],
        projects: [],
        work_history: [],
      });
      setMessage("Saved.");
    } catch (e) {
      setMessage(e instanceof Error ? `Failed to save: ${e.message}` : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <main className="mx-auto max-w-2xl px-6 py-10 text-sm text-muted">Loading…</main>;

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-ink">Your profile</h1>
        <Link href="/" className="text-sm font-medium text-accent underline">
          ← Back to dashboard
        </Link>
      </div>
      <p className="mb-6 text-sm text-muted">
        This drives every score, every tailored resume, and every cover letter — the AI never invents experience
        beyond what's here.
      </p>

      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <Field label="Full name">
          <input required value={form.full_name} onChange={(e) => set("full_name", e.target.value)} className={inputCls} />
        </Field>
        <Field label="Email">
          <input required type="email" value={form.email} onChange={(e) => set("email", e.target.value)} className={inputCls} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Phone">
            <input value={form.phone} onChange={(e) => set("phone", e.target.value)} className={inputCls} />
          </Field>
          <Field label="Current location">
            <input value={form.location} onChange={(e) => set("location", e.target.value)} className={inputCls} placeholder="Chennai, India" />
          </Field>
          <Field label="LinkedIn URL">
            <input value={form.linkedin_url} onChange={(e) => set("linkedin_url", e.target.value)} className={inputCls} />
          </Field>
          <Field label="GitHub URL">
            <input value={form.github_url} onChange={(e) => set("github_url", e.target.value)} className={inputCls} />
          </Field>
        </div>
        <Field label="Skills (comma-separated)">
          <input value={form.skills} onChange={(e) => set("skills", e.target.value)} className={inputCls} placeholder="Python, SQL, Machine Learning, Pandas" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Years of experience">
            <input type="number" step="0.5" min="0" value={form.experience_years} onChange={(e) => set("experience_years", e.target.value)} className={inputCls} />
          </Field>
          <Field label="Minimum salary (optional)">
            <input type="number" value={form.min_salary} onChange={(e) => set("min_salary", e.target.value)} className={inputCls} />
          </Field>
        </div>
        <Field label="Preferred locations (comma-separated)">
          <input value={form.preferred_locations} onChange={(e) => set("preferred_locations", e.target.value)} className={inputCls} placeholder="Bangalore, Chennai, Hyderabad, Pune" />
        </Field>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={form.remote_ok} onChange={(e) => set("remote_ok", e.target.checked)} className="accent-accent" />
          Open to remote roles
        </label>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Work authorization">
            <input value={form.work_authorization} onChange={(e) => set("work_authorization", e.target.value)} className={inputCls} placeholder="e.g. Indian citizen, no sponsorship needed" />
          </Field>
          <Field label="Notice period (days)">
            <input type="number" value={form.notice_period_days} onChange={(e) => set("notice_period_days", e.target.value)} className={inputCls} />
          </Field>
        </div>

        <p className="text-xs text-muted">
          Work authorization and notice period are stored here so any auto-filled application answer comes from what
          you actually entered — never guessed.
        </p>

        <button type="submit" disabled={saving} className="mt-2 self-start rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
          {saving ? "Saving…" : "Save profile"}
        </button>
        {message && <p className="text-sm text-muted">{message}</p>}
      </form>
    </main>
  );
}

const inputCls = "w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-accent";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}
