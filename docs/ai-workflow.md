# Antigravity AI Pair-Programming Workflow & Starter Archive

This document preserves the initial scaffolding and rules of engagement used to build the Hybrid Cloud Disaster Recovery Orchestrator pair-programming alongside Google DeepMind Antigravity.

---

## 1. Antigravity Agent Architecture

The project was constructed using specialized phase skills and invariant rule enforcement under `.agents/`:

| Path | Purpose |
|---|---|
| `AGENTS.md` | Always-on master instructions, phase protocol, and skill execution tables |
| `.agents/rules/safety-and-spend.md` | Non-negotiable cloud spend ceilings, credential hygiene, and guarded chaos boundaries |
| `.agents/rules/terraform-standards.md` | Module layout, pinned providers, validation blocks, and S3 native state locking |
| `.agents/rules/python-standards.md` | PEP 8, Pydantic v2 validation, strict typing (`mypy --strict`), and pure state machines |
| `.agents/rules/ansible-standards.md` | Role modularity, idempotent playbooks, and secure variable passing |
| `.agents/rules/docs-and-diagrams.md` | Mermaid diagram syntax, runbook standard structure, and empirical metric citation rules |

---

## 2. Phase Protocol Enforced by Agent

Every engineering phase followed an 8-step protocol:
1. **Plan First:** Generate an Implementation Plan artifact with files, commands, risks, and approvals.
2. **Task List:** Maintain active task status and verification gates.
3. **Build in Small Steps:** Complete, production-ready code with zero placeholders.
4. **Verify with Evidence:** Real command execution, JSON outputs, and test logs.
5. **Walkthrough Artifact:** 6-part standardized report (Goal, Files, Run it, Verify it, Common failures, Interview bullets).
6. **Progress Tracking:** Update `docs/PROGRESS.md` and `docs/interview-notes.md`.
7. **Conventional Commits:** Structured git commits with `gitleaks` pre-commit scans.
8. **Next Phase Handoff:** Clean terminal boundary and explicit slash command prompt.

---

## 3. Initial Kickoff Prompt Template (Archived)

```markdown
Read AGENTS.md and docs/project-spec.md, then run the dr-phase-0-plan skill.

My environment:
- Host OS: macOS (Darwin arm64)
- On-prem lab: Docker Compose Lite Mode (FastAPI, Nginx, PostgreSQL 16)
- AWS: Account 758579869433, Region ap-southeast-2 (Sydney), Profile dr-sandbox
- Budget ceiling: $15.00/month (standing compute: $0.00)
- Stack: Terraform 1.10+, Ansible Core 2.21, Python 3.11, Docker CE
```
