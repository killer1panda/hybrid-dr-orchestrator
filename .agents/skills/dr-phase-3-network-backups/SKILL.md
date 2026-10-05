---
name: dr-phase-3-network-backups
description: "Builds Phase 3 of the Hybrid DR project: WireGuard site-to-site tunnel, continuous Postgres backups with WAL archiving to S3, on-prem heartbeats, and a scheduled restore-test job. Use when starting or resuming Phase 3 or when asked about backups, RPO, WAL archiving or the tunnel."
---

# Phase 3: hybrid network and backups

Follow the phase protocol in AGENTS.md. Prerequisites: Phases 1 and 2 complete; ADR-003 and ADR-004 accepted.

## Deliverables
1. **WireGuard** (Ansible role `wireguard`, templates in `infra/networking/`). The on-prem side initiates with a persistent keepalive so it works behind NAT. Generate keys locally; never print them to chat or commit them (SOPS or Ansible Vault). The AWS endpoint lives in the DR environment unless ADR-003 approved an always-on witness. Document what the tunnel is used for: orchestrator-to-site probes, fencing, failback resync.
2. **Backups.** Compare pgBackRest, pg_basebackup plus `archive_command`, and WAL-G in a short table; pick one and record why. Schedule: weekly full, daily differential or incremental, continuous WAL archiving to S3. Tune `archive_timeout` to meet the RPO and explain the trade-off (more, smaller WAL segments). Encrypt at repository level in addition to S3 server-side encryption. Define retention.
3. **Heartbeat.** On-prem pushes a heartbeat to AWS (SSM parameter, S3 object or custom metric, per ADR-004) that the orchestrator and an AWS-side watchdog can read.
4. **Restore-test job.** A scheduled job restores the latest backup into a scratch instance or local container, checks row counts and the newest `rpo_probe` timestamp, and emits a pass or fail audit event. A failed restore test raises an alert.
5. Update `docs/runbook.md` with: take a manual backup, restore to a point in time, rotate the backup-writer credential.

## Approvals
Non-check `ansible-playbook` runs, and anything that writes to the real S3 bucket.

## Verification checklist (show real output)
- [ ] `pgbackrest info` (or the chosen tool's equivalent) shows a valid full backup and WAL range.
- [ ] A new WAL object appears in S3 within `archive_timeout` plus margin (show object timestamps).
- [ ] The restore test passes and reports the age of the newest `rpo_probe` row.
- [ ] Tunnel up: handshake age shown; tunnel down (stop the interface) detected; tunnel recovers on its own.
- [ ] Heartbeat visible in AWS and goes stale when the on-prem sender is stopped.
- [ ] No keys or credentials in git (`gitleaks`).
