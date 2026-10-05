---
name: dr-phase-8-portfolio
description: "Builds Phase 8 of the Hybrid DR project: the final README, demo script, lessons-learned and limitations, resume bullets built only from measured results, and interview preparation. Use when starting or resuming Phase 8 or when asked to polish, document or present the project."
---

# Phase 8: portfolio polish

Follow the phase protocol in AGENTS.md. Prerequisites: Phases 1 to 7 complete and at least three recorded drills in `docs/rto-rpo-report.md`.

## Deliverables
1. **README.md**: the problem in two sentences; architecture diagram; a 60-second quickstart for the non-hardware parts; a results table copied from `docs/rto-rpo-report.md`; the cost summary; limitations. Add status badges for the CI workflows.
2. **`docs/demo-script.md`**: a 2-minute video script with a shot list and the exact commands for the live drill. Optionally use the browser to record the Grafana and Route 53 steps (read-only; ask before clicking).
3. **Lessons learned and limitations**, honest: split-brain edge cases, DNS TTL, single region, single operator, lab versus production gaps, what you would do differently.
4. **Resume bullets (3 to 5).** Every number must come from `docs/rto-rpo-report.md` or a cited source. If a measurement is missing, say so and leave a clearly marked placeholder. Never invent metrics.
5. **Ten interview questions with strong answers**, each anchored in this project's real decisions and ADRs (for example why pilot light, why the control plane sits outside the failure domain, how fencing works and where it fails, how RPO was measured).
6. `docs/interview-notes.md` tidied into a one-page cheat sheet.
7. Clean-up: move `START_HERE.md` and `KICKOFF_PROMPT.md` into `docs/ai-workflow.md` (or remove them), run the full-history secret scan, and run /dr-teardown.

## Verification checklist (show real output)
- [ ] Fresh-clone test: follow the README from scratch in a clean container or VM through lint, tests and `terraform plan`, and fix every gap found.
- [ ] Every number in README and resume bullets traces to a source.
- [ ] `gitleaks` is clean across history.
- [ ] A tag query shows no billable DR resources remain.
