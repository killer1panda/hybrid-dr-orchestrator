---
name: dr-phase-4-dr-environment
description: "Builds Phase 4 of the Hybrid DR project: the on-demand AWS replica as Terraform modules and Ansible roles, plus the database restore and smoke-test playbooks, proven manually before automation. Use when starting or resuming Phase 4 or when asked to build or time the DR environment."
---

# Phase 4: DR environment as code

Follow the phase protocol in AGENTS.md. Prerequisites: Phases 1 to 3 complete. Prove everything by hand first; the orchestrator in Phase 5 only automates what works here.

## Deliverables
1. **Terraform** in `infra/aws/modules/` (vpc, compute, monitoring) and root `infra/aws/envs/dr/`: a single public subnet, security groups, one EC2 instance with an instance profile, an Elastic IP, tags `AutoTeardown=true`. Resolve the AMI through an SSM parameter or data source, never a hard-coded ID. Avoid NAT gateways and load balancers (cost). Choose access method in the plan and justify it: SSM Session Manager, or SSH restricted to the orchestrator's address with the key kept in SSM.
2. **Make targets** `dr-up` and `dr-down`. `dr-down` refuses to run if the state contains the backup bucket or anything from the persistent root.
3. **Ansible**: reuse roles; add `playbooks/restore_db.yml` (restore the newest backup and replay WAL to the latest point), `playbooks/site.yml` for the DR host, and `playbooks/smoke_tests.yml` (app `/healthz`, an item write and read, a check that the newest `rpo_probe` row is present).
4. **Timing sheet**: record the duration of each step (provision, configure, restore, smoke tests) in a draft of `docs/rto-rpo-report.md`. If the total exceeds the RTO budget, measure first, then consider baking an AMI to cut configure time.
5. Inventory generated from Terraform outputs.

## Parallel work
If you use parallel agents, split strictly by folder: Terraform in `infra/aws/**` and Ansible in `ansible/**`. Never let two agents edit the same file.

## Approvals
Every `terraform apply` and `ansible-playbook` against AWS; show the plan summary and per-run cost estimate first.

## Verification checklist (show real output)
- [ ] From nothing to a running app on AWS using only documented commands, with the elapsed time recorded.
- [ ] Smoke tests pass and show the age of the newest `rpo_probe` row.
- [ ] A second Ansible run reports `changed=0`.
- [ ] `make dr-down` leaves the persistent layer intact (bucket, zone, budget, parameter still present).
- [ ] A tag query shows no leftover billable resources after `dr-down`.
- [ ] The run's estimated and actual cost are in the spend ledger in docs/PROGRESS.md.
