const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN || "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_TOKEN}`,
      ...options.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return (await res.blob()) as unknown as T;
}

// ---------- Types (mirrors backend/app/schemas.py) ----------
export interface JobOut {
  id: number;
  source: string;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  description: string;
  tags: string[];
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  apply_url: string;
  posted_at: string | null;
}

export interface JobScoreOut {
  id: number;
  job_id: number;
  skill_match_pct: number;
  location_match_pct: number;
  salary_match_pct: number;
  experience_match_pct: number;
  overall_score: number;
  matched_skills: string[];
  missing_skills: string[];
  computed_at: string;
}

export interface ScoredJobOut {
  job: JobOut;
  score: JobScoreOut;
}

export interface ProfileOut {
  id: number;
  full_name: string;
  email: string;
  phone?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  location?: string | null;
  skills: string[];
  experience_years: number;
  education: { school: string; degree: string; year: string }[];
  certificates: string[];
  projects: { name: string; description: string; tech: string[] }[];
  work_history: { company: string; title: string; start: string; end: string; bullets: string[] }[];
  preferred_locations: string[];
  remote_ok: boolean;
  min_salary?: number | null;
  work_authorization?: string | null;
  notice_period_days?: number | null;
}

export interface RefreshResult {
  fetched: number;
  new: number;
  scored: number;
  by_source: Record<string, number>;
  errors: string[];
}

export interface ApplicationStats {
  counts: Record<string, number>;
  response_rate: number;
  success_rate: number;
  total: number;
}

// ---------- API calls ----------
export const api = {
  getProfile: () => request<ProfileOut>("/profile"),
  saveProfile: (data: Partial<ProfileOut>) =>
    request<ProfileOut>("/profile", { method: "PUT", body: JSON.stringify(data) }),

  listJobs: (minScore = 0) => request<ScoredJobOut[]>(`/jobs?min_score=${minScore}&limit=100`),
  refreshJobs: () => request<RefreshResult>("/jobs/refresh", { method: "POST" }),

  generateCoverLetter: (jobId: number, tone = "professional") =>
    request<{ id: number; content: string }>("/cover-letters", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, tone }),
    }),

  tailorResume: (jobId: number) =>
    request<{ id: number }>("/resumes/tailor", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId }),
    }),

  saveApplication: (jobId: number) => request(`/applications/${jobId}`, { method: "POST" }),
  updateApplication: (id: number, data: { status?: string; notes?: string }) =>
    request(`/applications/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  applicationStats: () => request<ApplicationStats>("/applications/stats"),

  resumePdfUrl: (resumeId: number) => `${API_URL}/resumes/${resumeId}/export.pdf`,
};
