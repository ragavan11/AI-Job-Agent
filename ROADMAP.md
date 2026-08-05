# Roadmap

Phase 1 is in this repo and working. This is what comes next, in order —
each phase is meant to be a complete, working addition, not a stub.

## Phase 2 — Wider coverage + real tracking
- Read-only search (listings only, not applying) across LinkedIn, Indeed,
  Naukri, Foundit, and Glassdoor. Lower risk than automating a
  submission, but these platforms run real anti-bot defenses, so this
  needs rate-limiting and backoff, not a tight polling loop.
- Full applications dashboard: charts, response-rate/success-rate trends
  over time, not just the current-state numbers Phase 1 shows.
- AI memory: blocked/preferred companies, a history of past screening-
  question answers so tone/content stays consistent across applications.
- Notifications: desktop first, then email; Telegram/Discord as optional
  add-ons once the core notification logic exists.

## Phase 3 — Assisted application automation
The part that actually fills out and submits applications. Design
constraints that carry over from Phase 1's decisions:
- Playwright automation runs against **your own logged-in session** —
  no credential stuffing, no fingerprint-spoofing, no proxy rotation
  aimed at evading a platform's bot detection.
- **Human review is required before final submit**, non-optional for
  salary, visa/work-authorization, and notice-period fields specifically
  — those are the fields that actually hurt you if an AI guesses wrong.
- Start with Greenhouse/Lever/Ashby/Workday-based company forms, since
  their structure is consistent enough to generalize across companies.
  Arbitrary custom company career pages are a long tail — expect to
  tune per-company rather than expecting one flow to cover everyone.
- A trusted-flow auto-submit toggle becomes available per company/ATS
  type once you've verified it gets that flow right — opt-in, per flow,
  never a global default.

## Phase 4 — Extras
Gmail reading + recruiter-email detection + reply drafting, AI career
coach, salary prediction, resume-gap detection, Chrome extension, voice
commands, calendar integration, Telegram/Discord bots. Revisit which of
these actually earn a build once Phases 1-3 are in daily use — this is a
lot of surface area for a tool only one person uses.
