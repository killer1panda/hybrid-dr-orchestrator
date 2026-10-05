# Hybrid Cloud DR Orchestrator: project instructions

These instructions are always active. Keep them in mind on every turn.

## The project
An automated disaster-recovery orchestrator. A simulated on-prem private cloud (Proxmox VE, with a lite-mode KVM/Vagrant fallback) runs a 3-tier app. When that site fails, the orchestrator, with zero human intervention: confirms the failure, provisions a replica in AWS with Terraform, configures it with Ansible, restores the latest Postgres backup, smoke-tests, cuts DNS over with Route 53, notifies, and records measured RTO and RPO. It then fails back automatically and tears AWS down to stop costs.

Read before planning any phase: @docs/project-spec.md
Status, decisions, spend ledger: @docs/PROGRESS.md

## Who you are working with
A student building a portfolio project. Explain trade-offs briefly and define hybrid-networking and DR terms on first use. Never hand-wave: every step must be runnable and verifiable. Every decision must be explainable in an interview.

## Phases (each is a skill; the user starts one at a time)
| Phase | Skill | Output |
|---|---|---|
| 0 | /dr-phase-0-plan | decisions (ADRs), diagrams, cost model, schedule |
| 1 | /dr-phase-1-onprem | simulated on-prem site + sample app |
| 2 | /dr-phase-2-aws-foundation | persistent AWS layer: state, IAM, backup bucket, DNS zone, budget |
| 3 | /dr-phase-3-network-backups | WireGuard tunnel, backups + WAL archiving, restore-test job |
| 4 | /dr-phase-4-dr-environment | on-demand AWS replica (Terraform + Ansible), manual restore proven |
| 5 | /dr-phase-5-orchestrator | Python state machine, monitor, actions, tests |
| 6 | /dr-phase-6-failback-chaos | chaos drills, failback, measured RTO/RPO |
| 7 | /dr-phase-7-ci-security | observability, CI/CD, security hardening |
| 8 | /dr-phase-8-portfolio | README, demo script, interview prep |

Utilities: /dr-verify (verification gate), /dr-teardown (stop AWS costs).
If a slash command is not offered, the user can ask for a skill by name, for example "use the dr-phase-1-onprem skill".
Never start a phase the user has not asked for. Never skip ahead.

## Phase protocol (every phase)
1. **Plan first.** Before editing files, produce an Implementation Plan artifact (the /plan command does this) listing files, commands, risks and what needs approval. Wait for the user's go-ahead.
2. **Keep the Task List current.** The last task is always verification.
3. **Build in small steps.** Every file is complete: no "..." placeholders, no "add your logic here".
4. **Verify with evidence.** Run the phase's checklist (or /dr-verify) and capture real command output or screenshots. Never write "should work".
5. **Finish with a Walkthrough artifact** in this six-part format: Goal of this step; Files; Run it; Verify it (checklist plus actual output); Common failure modes and fixes; What I should understand (3 bullets, useful in interviews).
6. **Update docs/PROGRESS.md** (phase status, decisions, spend ledger) and append the 3 interview bullets to docs/interview-notes.md.
7. **Propose a conventional-commit message.** Do not push.
8. **Stop.** End by naming the next phase's slash command from the table above (for example: "Phase 2 complete. Start Phase 3 with /dr-phase-3-network-backups when ready."). Do not begin it.

## Facts to verify, never remember
Versions of Terraform, providers, Ansible collections and the AWS CLI; AWS Free Tier and credit rules; eligible instance types; prices; current backend-locking and security-tool recommendations. Look them up in official docs or registries and record the URL next to the decision in docs/PROGRESS.md. Label any number you could not verify as an estimate.

## When something fails
Read the whole error. State a hypothesis. Change one thing at a time. After two failed attempts, stop and report what you tried and learned. Never widen permissions, disable the terminal sandbox, skip TLS verification, or add -auto-approve to get past an error.

## Style
Concise. Explain why, not just what. Numbers in docs come from measurements or cited sources, never invented.
