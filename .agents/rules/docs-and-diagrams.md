---
trigger: model_decision
description: "Apply when writing or editing documentation in docs/, ADRs, runbooks, the README, or Mermaid diagrams for the Hybrid DR project."
---

# Documentation and diagram standards

- ADRs live in `docs/decisions/` and follow `ADR-TEMPLATE.md`: Context, Options (table), Decision, Consequences, What would change this decision.
- Diagrams are Mermaid in fenced blocks inside the doc that explains them. Keep node labels short, quote labels that contain parentheses or colons, and re-read the syntax before saving.
- Runbooks follow: Symptom, Diagnosis (commands plus expected output), Action, Verify, Rollback.
- Every number (cost, RTO, RPO, duration) cites its source: a drill ID from `docs/rto-rpo-report.md` or an official URL. Unmeasured numbers are labeled "estimate".
- Write for a stranger who has never seen the project: define terms on first use, list prerequisites, keep commands copy-pasteable.
- Keep each doc focused and link instead of repeating.
