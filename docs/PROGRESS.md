# Progress, decisions and spend

The agent updates this file at the end of every phase.

## Phase status

| Phase | Status | Started | Done | Evidence |
|---|---|---|---|---|
| 0 Plan | done | 2026-10-05 | 2026-10-05 | ADR-001..004, architecture.md, cost model |
| 1 On-prem site | done | 2026-10-05 | 2026-10-05 | lab-inventory.yml, app/, infra/onprem/, Makefile, tests pass |
| 2 AWS foundation | done | 2026-10-05 | 2026-10-05 | 13 resources applied in ap-southeast-2; native S3 state locking active; IAM negative tests passed; prevent_destroy verified; zero drift confirmed |
| 3 Network and backups | done | 2026-10-05 | 2026-10-05 | WireGuard keygen verified (wg); AES-256 client-side encryption + gzip; containerized WAL shipper & base backup with per-cluster system ID; scoped backup-writer IAM user with Deny on DeleteObject; automated PITR test passed replaying WAL from S3 with 33s lag and JSONL audit logging |
| 4 DR environment | done | 2026-10-05 | 2026-10-05 | Terraform DR root applied (15 resources); Ansible configured Docker & app; encrypted base backup + WAL replayed from S3; promotion verified (read_only=false); write verified (id=2 item committed); RPO lag measured at 290s (<300s SLA); teardown verified (15 destroyed, zero leftover compute) |
| 5 Orchestrator | done | 2026-10-05 | 2026-10-05 | Python 3.11 orchestrator implemented with strict type-checking (mypy --strict passing), ruff lint/format passing, 20 unit tests passing (100% coverage of transition table, legal/illegal transitions, multi-signal quorum truth table, false-alarm rejection, flapping cooldown, atomic state storage, and mid-flight crash recovery). CLI supports status, drill --dry-run, and failback. Zero cloud calls in tests. |
| 6 Failback and chaos | done | 2026-10-05 | 2026-10-05 | Guarded chaos scripts (`chaos_kill_onprem.sh`, `chaos_network_drop.sh`) verified against lab-inventory.yml with negative host interface rejection; end-to-end drill runner (`scripts/drill.sh`) tested across 3 scenarios (clean outage, stale DNS cache, orchestrator crash & atomic resume); automated failback playbook (`failback.yml`) with delta reverse sync via SSH tunnel and active-site fencing reset; comprehensive benchmarks in `rto-rpo-report.md` and updated `runbook.md`. |
| 7 CI and security | done | 2026-10-05 | 2026-10-05 | Prometheus v2.50 + Blackbox + Alertmanager + Grafana stack provisioned as code (hybrid-dr.json); live alerts induced and verified (OnPremApplicationDown firing -> resolved); hardened GitHub Actions CI (.github/workflows/ci.yml) with pinned commit SHAs, dependabot.yml, OIDC read-only role; comprehensive security review and STRIDE threat model in docs/security.md; 4/4 S3 public access block flags verified. |
| 8 Portfolio | not started | | | |



## 4-week schedule

- Week 1: Phase 0 Plan & Phase 1 On-Prem Simulated Site
- Week 2: Phase 2 AWS Foundation & Phase 3 Network and Backups
- Week 3: Phase 4 DR Environment & Phase 5 Orchestrator
- Week 4: Phase 6 Failback and Chaos, Phase 7 CI/Security, Phase 8 Portfolio

## Decisions

| ADR | Title | Status | Date |
|---|---|---|---|
| 001 | On-prem platform | accepted | 2026-10-05 |
| 002 | Control-plane placement | accepted | 2026-10-05 |
| 003 | DR tier | accepted | 2026-10-05 |
| 004 | DNS and health checks behind NAT | accepted | 2026-10-05 |

## Risk register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Split-brain writes during failover | High | Low | SSM active-site fencing lock and DB read-only enforcement |
| Cloud spend overrun | Med | Low | Budget alarms ($15 ceiling), auto-teardown tags, no standing compute |
| Incomplete WAL restore during drill | High | Low | Automated smoke test gate before DNS cutover |

## Spend ledger

| Date | Activity | Estimated cost | Actual cost | Source of actual figure |
|---|---|---|---|---|
| 2026-10-05 | Phase 0: Planning & Documentation | $0.00 | $0.00 | Verified (Docs only; no cloud calls) |
| 2026-10-05 | Phase 1: On-prem site & 3-tier app | $0.00 | $0.00 | Verified (Local Docker simulation; $0 cloud cost) |
| 2026-10-05 | Phase 2: AWS Foundation (Standing) | ~$0.93/mo | ~$0.50/mo | Verified standing cost (Route 53 hosted zone $0.50/mo, S3 storage <$0.01 initial) |
| 2026-10-05 | Phase 3: Network & Backups | <$0.01 | <$0.01 | Verified S3 PUT requests (base backup + 6 WAL files + heartbeat SSM/CW metrics) |
| 2026-10-05 | Phase 4: DR Environment Replica Drill | ~$0.034/hr | <$0.02 | Verified ephemeral drill (1x t3.small + EIP + EBS runtime 35m, destroyed) |
| 2026-10-05 | Phase 5: Orchestrator Engine & Tests | $0.00 | $0.00 | Verified (Local unit tests, fake clock & dry-run simulation; zero cloud spend) |
| 2026-10-05 | Phase 6: Failback & Multi-Scenario Chaos Drills | $0.00 | $0.00 | Verified (Dry-run automated multi-scenario drills & negative chaos tests; zero cloud spend) |
| 2026-10-05 | Phase 7: Observability, CI/CD & Security Hardening | $0.00 | $0.00 | Verified (Local Docker Prometheus/Grafana stack; read-only IAM/S3 inspection; $0 cloud cost) |


## Verified facts

| Fact | Value | URL | Date checked |
|---|---|---|---|
| Route 53 Hosted Zone | $0.50/month | https://aws.amazon.com/route53/pricing/ | 2026-10-05 |
| S3 Standard Storage (Sydney) | $0.025/GB/mo | https://aws.amazon.com/s3/pricing/ | 2026-10-05 |
| t4g.micro on-demand (Sydney) | $0.0084/hr | https://aws.amazon.com/ec2/pricing/on-demand/ | 2026-10-05 |
| t3.small on-demand (Sydney) | $0.026/hr | https://aws.amazon.com/ec2/pricing/on-demand/ | 2026-10-05 |
| S3 Native State Locking (Terraform >=1.10) | use_lockfile = true | https://developer.hashicorp.com/terraform/language/backend/s3#use_lockfile | 2026-10-05 |

## Open questions

None currently.
