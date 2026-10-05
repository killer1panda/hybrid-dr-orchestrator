---
name: dr-phase-0-plan
description: "Runs Phase 0 (planning) of the Hybrid DR Orchestrator project. Gathers environment facts, settles four architecture decisions as ADRs, produces Mermaid architecture, sequence and state diagrams, a cost model and a 4-week schedule. Use at the very start of the project or when re-planning scope. Writes no infrastructure code."
---

# Phase 0: plan

Follow the phase protocol in AGENTS.md and read docs/project-spec.md. **Write docs only: no Terraform, no AWS API calls, no installs.** Looking facts up in official documentation is expected.

## 1. Gather facts (ask once, offer defaults)
Skip anything the kickoff message already answers. Ask the rest in ONE batch of at most 8 questions, each with a recommended default:
1. Host machine: OS, CPU virtualization and nested-virtualization support, RAM, free disk.
2. On-prem lab: Proxmox on bare metal, Proxmox nested in a hypervisor, or lite mode (KVM/libvirt, Vagrant).
3. AWS: new or existing account, credits versus legacy free tier, preferred region, MFA or SSO in place, monthly cost ceiling.
4. Domain: owns one, or use a Route 53 test zone.
5. GitHub repo name and visibility; whether CI may assume an AWS role through OIDC.
6. Notification channel: Slack, Discord or email.
7. Weekly hours and target finish date.
8. Already installed: Terraform, Ansible, Docker, Python versions.

Before recommending instance sizes, check the current AWS Free Tier and credit rules and the eligible instance types on the official AWS pages. Do not rely on memory.

## 2. Settle four decisions as ADRs
Create `docs/decisions/ADR-00N-<slug>.md` from ADR-TEMPLATE.md. Present options in a table, recommend one, and wait for the user's approval.

| ADR | Decision | Starting recommendation |
|---|---|---|
| 001 | Proxmox vs OpenStack vs lite mode | Proxmox (nested if needed). OpenStack only as a stretch. Explain in five lines: footprint, install effort, API surface. |
| 002 | Where the orchestrator runs | Outside the on-prem failure domain. Compare a tiny always-on AWS witness, Lambda + EventBridge + CodeBuild, and a separate control VM for the demo (limitation documented). |
| 003 | DR tier | Pilot light (S3 backups + WAL, AWS built on demand) versus warm standby. Show a cost and RTO table. Recommend pilot light. |
| 004 | DNS and health checks behind home NAT | Route 53 endpoint health checks cannot reach a NAT'd lab directly. Compare (a) exposing a health endpoint through a tunnel or reverse proxy; (b) on-prem heartbeats pushed to AWS as a standard-resolution custom metric, with a CloudWatch alarm feeding a Route 53 health check of type "state of CloudWatch alarm data stream" (it does not support M-out-of-N alarms, high-resolution metrics or metric math; set the insufficient-data behavior deliberately) plus failover routing; (c) on-prem heartbeats plus orchestrator-driven record updates. Recommend (c) as primary, because DNS must only switch after fencing is set and the DR environment has passed smoke tests, which native failover routing does not coordinate; keep (b) as a fallback demo and an extra signal. Verify details and cost in the current Route 53 docs. TTL 30 to 60 s. |

## 3. Produce
- `docs/architecture.md`: Mermaid C4 context and container diagrams, the failover sequence diagram, the state machine diagram, and its transitions table (from, to, guard, timeout, retries, action, on-failure).
- RPO and RTO targets (default RPO <= 5 min, RTO <= 15 min) with a time budget per RTO step: detect, provision, configure, restore, validate, DNS.
- Cost model: monthly estimate for the persistent layer and cost per drill. Label every figure an estimate and cite its source URL.
- AWS one-time bootstrap checklist (manual, documented): sandbox account or OU, MFA on root and no root keys, budget and alerts, a least-privilege profile named `dr-sandbox`, region lock, and export of `DR_ALLOWED_ACCOUNT_ID`.
- `docs/PROGRESS.md`: fill in the phase table, the 4-week schedule, and a risk register (top 8 risks with mitigations).
- Confirm `.gitignore` exists before any other file is created.

## Verification checklist
- [ ] All four ADRs exist and the user approved them.
- [ ] Mermaid diagrams are syntactically valid and consistent with the ADRs.
- [ ] Every number is cited or labeled estimate.
- [ ] The AWS bootstrap checklist is complete enough that the user can follow it without help.
- [ ] No infrastructure code or cloud call was made.
