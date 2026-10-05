---
name: dr-phase-6-failback-chaos
description: "Builds Phase 6 of the Hybrid DR project: guarded chaos scripts, end-to-end drills with measured RTO and RPO, and automated failback with teardown. Use when starting or resuming Phase 6 or when asked to run a drill, measure RTO or RPO, or test failback."
---

# Phase 6: chaos drills and failback

Follow the phase protocol in AGENTS.md and the safety rule. Prerequisites: Phases 1 to 5 complete.

## Deliverables
1. **Chaos scripts** `scripts/chaos_*.sh` (stop lab VMs through the hypervisor API or CLI, drop the WireGuard interface, block egress on the lab bridge). Each reads `lab-inventory.yml`, supports `--help` and `--dry-run`, requires `--confirm`, logs to the audit trail, and refuses anything outside the allow-list or any host interface.
2. **`make drill`** and `scripts/drill.sh`: inject failure, let the orchestrator run, wait for recovery, print the report.
3. **Measurement** (see project-spec section 4.6):
   - RTO: from the audit log, failure injection to the first successful external probe of the new endpoint, with per-step durations.
   - RPO: failure time minus the newest `rpo_probe` timestamp in the restored database.
4. **Drill scenarios (minimum three):** clean outage; outage with a stale DNS cache on the client; orchestrator crash mid-failover. Record each as a numbered drill in `docs/rto-rpo-report.md` with a results table and a Mermaid Gantt of the step timeline.
5. **Failback** (`make failback`, `ansible/playbooks/failback.yml`): bring on-prem back; resync data from AWS to on-prem; verify row counts and probe continuity; short write freeze; return DNS; move the fencing flag back; tear the DR environment down through the /dr-teardown logic. If resync fails, stay on AWS and alert.
6. Update `docs/runbook.md` with the manual override and recovery paths.

## Approvals
Each drill creates billable AWS resources: show the estimate and get approval. Chaos scripts run only after `--dry-run` output has been reviewed.

## Verification checklist (show real output)
- [ ] `make drill` completes end to end with no human input after the injection; the report prints RTO and RPO.
- [ ] Before and after DNS lookups show the cutover and the return.
- [ ] Three drills recorded with real numbers; targets met or the gap explained.
- [ ] `make failback` returns service to on-prem; the DR environment is gone (tag query empty); the persistent layer is intact.
- [ ] A chaos script run against a non-allow-listed target is refused (show it).
