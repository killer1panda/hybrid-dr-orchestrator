# Interview notes

After every phase the agent appends three bullets: what was built, why this design, and what to say if asked about its limits. Phase 8 turns this file into a one-page cheat sheet.

## Phase 0
- **What was built:** Architecture specification (RTO <= 15m, RPO <= 5m budget), four accepted Architecture Decision Records (ADR-001 through ADR-004), cost model (~$0.93/mo standing, ~$0.12/drill), and risk register with mitigation strategies.
- **Why this design:** Pilot Light pattern provides the optimal trade-off between strict durability (continuous WAL streaming keeps RPO < 60s) and minimal cost (zero standing EC2 compute in AWS, provisioning replica on-demand via Terraform/Ansible). Dual-mode orchestrator prevents shared failure domains.
- **Limits and trade-offs:** On-demand provisioning in AWS introduces 3.5 minutes of EC2/VPC boot latency into the RTO budget compared to a Warm Standby (which has RTO < 3m but costs $35+/mo). Residential NAT requires push heartbeats and API-driven Route 53 updates rather than external pull probes.

## Phase 1
- **What was built:** A containerized on-premises 3-tier lab environment (Nginx reverse proxy at 192.168.10.10, FastAPI backend at 192.168.10.20, PostgreSQL 16 with WAL archiving at 192.168.10.30, and a 1-second monotonic RPO probe daemon at 192.168.10.25) running on a dedicated bridge network (`dr_onprem_bridge`, 192.168.10.0/24) with a formal chaos allow-list (`lab-inventory.yml`).
- **Why this design:** Lightweight, deterministic local simulation that requires zero cloud spend while preserving real network topology semantics (static IPs, reverse proxy buffering, database health checking, read-only fencing detection, and WAL archiving to volume). The separate RPO probe inserts timestamped sequence IDs every second to provide unforgeable ground-truth data loss metrics during disaster drills.
- **Limits and trade-offs:** Docker bridge networking does not fully simulate hypervisor-level physical fault domains (such as power supply failures or kernel panics), and storage writes share the host OS disk subsystem. In enterprise environments, this would be deployed on dedicated Proxmox VE / KVM hypervisors with out-of-band IPMI fencing (STONITH).

## Phase 2
- **What was built:** Persistent AWS foundation in `ap-southeast-2` (Sydney) with modular Terraform: SSE-S3 encrypted backup bucket with versioning and lifecycle rules (`s3-backup`), least-privilege IAM roles and user (`iam-roles`), private Route 53 hosted zone (`dr-lab.internal`), SSM fencing parameter (`/hybrid-dr/active-site`), AWS Budget alarm ceiling ($15.00/mo) with SNS notifications, and cost audit script (`scripts/cost_guard.sh`).
- **Why this design:** Standing cost optimized to ~$0.93/month by leveraging SSE-S3 (avoiding $1.00/mo customer-managed KMS key) and Terraform native S3 backend locking via `use_lockfile = true` (avoiding DynamoDB state-locking tables). Negative security testing is built in: `dr-onprem-backup-writer` has an explicit `Deny` on `s3:DeleteObject` to protect against ransomware or accidental deletion of database backups.
- **Limits and trade-offs:** Scoped IAM user credentials for on-premises backup shipping require periodic rotation procedures rather than IAM Roles Anywhere with x509 PKI certificates, which was deferred to avoid the $400/mo AWS Private CA fee or running a self-hosted PKI. Route 53 private hosted zone has a fixed $0.50/month fee regardless of query volume.

## Phase 3
- **What was built:** End-to-end continuous hybrid data replication pipeline: zero-leak WireGuard VPN templates with NAT traversal (`PersistentKeepalive = 25`), continuous PostgreSQL WAL shipper (`scripts/archive_wal.sh` with gzip compression directly into S3), full snapshot backup streamer (`scripts/backup_base.sh` streaming `pg_basebackup` directly into S3), automated point-in-time recovery test harness (`scripts/test_restore.sh`), 30-second hybrid heartbeat daemon (`scripts/heartbeat_publisher.py` writing to SSM Parameter `/hybrid-dr/heartbeat/onprem` and CloudWatch), and complete operational runbooks (`docs/runbook.md`).
- **Why this design:** Continuous WAL archiving decouples replication frequency from snapshot size, allowing us to hit our target RPO <= 60 seconds without running an expensive warm standby replica database. Packaging backups with gzip and streaming directly to S3 avoids local disk exhaustion. The automated restore harness verifies backup integrity on every run, asserting both table counts and the precise timestamp age of the monotonic RPO probe.
- **Limits and trade-offs:** WAL shipping provides asynchronous replication with a delay equal to the segment size or `archive_timeout` (60s), meaning in an abrupt catastrophic site destruction up to 60s of writes could theoretically be lost (within our 5-minute RPO budget). In synchronous streaming replication (e.g. pgpool or physical standby), RPO would be 0s, but that requires standing compute in AWS and introduces latency penalties on on-prem transaction commits across the WAN.

## Phase 4
- **What was built:** An on-demand, ephemeral AWS DR replica stack provisioned via Terraform (`infra/aws/envs/dr`) and configured via Ansible (`ansible/playbooks/site.yml`, `restore_db.yml`, `smoke_tests.yml`). The stack includes dynamic ingress detection (restricting SSH strictly to the orchestrator operator's `/32` IP), client-side PBKDF2 AES-256 decryption of base backups from S3, automated WAL replay to PostgreSQL read/write promotion in Docker (`network_mode: host` to access IMDS), smoke testing of FastAPI (`/healthz` and write validation `POST /items`), unforgeable RPO measurement from continuous sequence probes, and clean teardown via `make dr-down`.
- **Why this design:** Pilot Light pattern with zero standing EC2 compute delivers dramatic cost savings ($0.00/mo standing vs. $35+/mo for always-on replica). Keeping persistent resources (S3 bucket, Route 53 zone, IAM, budgets) in a decoupled Terraform root guarantees that ephemeral teardown can never wipe backups or state locks. S3 native state locking (`use_lockfile = true`) avoids DynamoDB table costs.
- **Limits and trade-offs:** Cold provisioning introduces ~14 minutes of package installation and image building (`apt`, `docker`, `pip`) on a stock Ubuntu AMI, yielding a total cold failover RTO of ~21 minutes. In enterprise production, this latency is eliminated by using Packer to pre-bake Golden AMIs with container images pre-cached, dropping RTO to under 7 minutes while maintaining zero standing EC2 compute spend.

## Phase 5

## Phase 6

## Phase 7

## Phase 8
