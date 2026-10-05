# Progress, decisions and spend

The agent updates this file at the end of every phase.

## Phase status

| Phase | Status | Started | Done | Evidence |
|---|---|---|---|---|
| 0 Plan | done | 2026-10-05 | 2026-10-05 | ADR-001..004, architecture.md, cost model |
| 1 On-prem site | done | 2026-10-05 | 2026-10-05 | lab-inventory.yml, app/, infra/onprem/, Makefile, tests pass |
| 2 AWS foundation | done | 2026-10-05 | 2026-10-05 | 13 resources applied in ap-southeast-2; native S3 state locking active; IAM negative tests passed; prevent_destroy verified; zero drift confirmed |
| 3 Network and backups | not started | | | |
| 4 DR environment | not started | | | |
| 5 Orchestrator | not started | | | |
| 6 Failback and chaos | not started | | | |
| 7 CI and security | not started | | | |
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

## Verified facts

| Fact | Value | URL | Date checked |
|---|---|---|---|
| Route 53 Hosted Zone | $0.50/month | https://aws.amazon.com/route53/pricing/ | 2026-10-05 |
| S3 Standard Storage (Sydney) | $0.025/GB/mo | https://aws.amazon.com/s3/pricing/ | 2026-10-05 |
| t4g.micro on-demand (Sydney) | $0.0084/hr | https://aws.amazon.com/ec2/pricing/on-demand/ | 2026-10-05 |
| S3 Native State Locking (Terraform >=1.10) | use_lockfile = true | https://developer.hashicorp.com/terraform/language/backend/s3#use_lockfile | 2026-10-05 |

## Open questions

None currently.
