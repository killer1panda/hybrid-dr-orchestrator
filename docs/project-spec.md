# Project specification: Automated Hybrid Cloud DR Orchestrator

## 1. Goal and definition of done

Build an orchestrator that, when a simulated on-prem private cloud suffers a catastrophic failure, does the following with **zero human intervention**:

1. Detects and confirms the failure (no false positives from a single missed check).
2. Provisions a replica environment in AWS using Terraform.
3. Configures the instances using Ansible.
4. Restores the latest database backup into the AWS environment.
5. Runs smoke tests against the new environment.
6. Updates DNS (Amazon Route 53) to route traffic to AWS.
7. Notifies the owner (Slack, Discord or email webhook) and records an audit log with RTO and RPO measurements.
8. Fails back automatically once the private cloud is healthy, then tears down AWS resources to stop costs.

**Done means:**
- `make drill` triggers a simulated on-prem outage and the system recovers on AWS with no human input; measured RTO and RPO are printed in a report.
- `make failback` returns to on-prem and destroys the DR environment.
- `make teardown` leaves zero billable DR resources while backups, state and the DNS zone are untouched.
- CI is green; security scans pass or carry time-boxed waivers; a monthly AWS cost estimate (target: a few dollars) is documented.
- The docs let a stranger reproduce the project in under a day.

## 2. Constraints

- **Budget: near zero.** Free-tier-friendly resources only (verify current Free Tier or credit rules first). Tag everything, add an AWS Budget alarm, provide an automatic teardown path.
- **Hardware: one student laptop or desktop** (assume 16 GB RAM, possibly nested virtualization). Provide a lite mode (KVM/libvirt, Vagrant or similar) if Proxmox is too heavy. Recommend Proxmox over OpenStack for footprint reasons and explain why in five lines (ADR-001).
- **Everything is Infrastructure as Code.** No console clicking except the one-time AWS account and IAM bootstrap, which must be documented.
- **Idempotent and re-runnable.** Orchestrator runs must be safe to repeat.
- **Security:** least-privilege IAM; no secrets in git (SOPS, Ansible Vault, or SSM Parameter Store / Secrets Manager); encrypted backups (S3 server-side encryption plus repository-level encryption); a WireGuard site-to-site tunnel between on-prem and AWS.

## 3. Tech stack (use this unless you justify a change in an ADR)

| Layer | Choice |
|---|---|
| Private cloud (simulated on-prem) | Proxmox VE (primary); OpenStack as optional stretch |
| IaC | Terraform, modular; remote state in S3 (check current docs for the recommended locking method) |
| Config management | Ansible roles; inventory generated from Terraform outputs |
| Public cloud | AWS: EC2, VPC, S3, Route 53, IAM, CloudWatch, SNS, SSM |
| Orchestrator | Python 3.11+ state-machine service, packaged in Docker |
| Sample workload | 3-tier: Nginx -> FastAPI (or Flask) -> PostgreSQL |
| DB backup | pgBackRest (or pg_basebackup plus WAL archiving) to S3; explain the RPO impact |
| Hybrid networking | WireGuard site-to-site tunnel |
| Observability | Prometheus + Grafana on-prem; CloudWatch on AWS; structured JSON logs |
| CI/CD | GitHub Actions: terraform fmt/validate/plan, tflint, ansible-lint, pytest, ruff, mypy, trivy config or checkov, gitleaks |
| Testing | pytest, `terraform test` or Terratest, Molecule for Ansible roles, chaos scripts |

## 4. Architecture requirements

1. **Diagrams (Mermaid):** C4 context and container views, a failover sequence diagram, and the state machine. Keep them updated as decisions change.
2. **Failover state machine.** States: `HEALTHY -> DEGRADED -> FAILURE_CONFIRMED -> PROVISIONING -> RESTORING -> VALIDATING -> DNS_CUTOVER -> RUNNING_ON_AWS -> FAILBACK_PENDING -> FAILBACK_IN_PROGRESS -> HEALTHY`, plus `FAILED_NEEDS_HUMAN` as the safe terminal state. Provide a transitions table: from, to, guard, timeout, retries, action, on-failure. A maintenance-window flag suppresses failover. A cooldown prevents flapping.
3. **Health-check design.** Signal classes: application (HTTP 200 from `/healthz`, which checks the DB end to end), data (SQL or TCP check on Postgres), platform (Proxmox API or node status), liveness (VM heartbeat pushed to AWS), network (tunnel handshake age). Declare failure only after N consecutive failures across at least two independent signal classes AND an external vantage point agrees AND maintenance mode is off.
4. **Split-brain protection (fencing).** Before DNS cutover, set a fencing flag (for example SSM parameter `/hybrid-dr/active-site`). On-prem checks it periodically and, when reachable, sets Postgres `default_transaction_read_only = on`. Fail-safe: if on-prem cannot read the flag for T seconds, it goes read-only. Document the failure modes honestly: a partitioned (not dead) site with clients holding cached DNS can accept stale writes during the TTL window.
5. **DNS strategy.** Compare (a) Route 53 failover routing with health checks and (b) orchestrator-driven record updates through the API. Route 53 endpoint health checks cannot probe a lab behind home NAT without exposing an endpoint; an alarm-based health check ("state of CloudWatch alarm data stream") fed by a heartbeat metric is the alternative to evaluate. Settle this in ADR-004. TTL 30 to 60 seconds; document the propagation caveat. Use a cheap domain or a test hosted zone.
6. **Data strategy.** Targets: RPO <= 5 min, RTO <= 15 min (confirm in Phase 0). Show how backup cadence plus continuous WAL archiving (`archive_timeout`) achieves the RPO. Measure, do not assume:
   - RPO: a writer inserts a monotonic counter and UTC timestamp into `rpo_probe` every second; RPO = failure time minus the newest timestamp present in the restored database.
   - RTO: from the audit log, failure injection to the first successful external probe of the new endpoint, with per-step durations.
7. **Failback plan.** Reverse resync of data from AWS to on-prem, verification (row counts and probe continuity), a short write freeze, DNS return, fencing flag moved back, DR environment torn down. If resync fails, stay on AWS and alert.
8. **Control-plane placement (ADR-002).** The orchestrator must not live inside the failure domain it watches. Evaluate: a tiny always-on AWS witness; Lambda plus EventBridge plus CodeBuild; or a separate control VM or container for the demo with the limitation documented.
9. **DR tier (ADR-003).** Pilot light (S3 backups plus WAL, AWS built on demand) versus warm standby (small always-on replica). Show a cost and RTO table.
10. **Persistent versus ephemeral Terraform roots.** `infra/aws/persistent/` holds state, IAM, backup bucket, DNS zone, budget and the fencing parameter. `infra/aws/envs/dr/` holds the ephemeral DR environment. Teardown only ever touches the ephemeral root.

## 5. Repository structure

```
hybrid-dr-orchestrator/
├── AGENTS.md
├── README.md                  # written in Phase 8
├── lab-inventory.yml          # allow-list for chaos tooling
├── docs/
│   ├── architecture.md
│   ├── project-spec.md
│   ├── PROGRESS.md
│   ├── interview-notes.md
│   ├── decisions/             # ADR-001 ... ADR-004+
│   ├── runbook.md
│   ├── rto-rpo-report.md
│   ├── security.md
│   └── diagrams/
├── infra/
│   ├── onprem/                # Proxmox (or lite-mode) Terraform + cloud-init
│   ├── aws/
│   │   ├── modules/           # vpc, compute, s3-backup, route53, iam, monitoring
│   │   ├── persistent/
│   │   └── envs/dr/
│   └── networking/            # WireGuard templates
├── ansible/
│   ├── inventories/
│   ├── roles/                 # common, nginx, app, postgres, wireguard, node_exporter
│   └── playbooks/             # site.yml, restore_db.yml, smoke_tests.yml, failback.yml
├── app/                       # sample 3-tier workload + Dockerfile
├── orchestrator/
│   ├── src/hybrid_dr/         # config, signals, quorum, state_machine, actions, notifier, audit, cli
│   ├── tests/
│   ├── Dockerfile
│   └── config.example.yaml
├── scripts/                   # chaos_*.sh, drill.sh, cost_guard.sh
├── .github/workflows/
├── .agents/                   # rules and skills for Antigravity
└── Makefile
```

## 6. Code quality

- Terraform: modules with variables, outputs, validation blocks, pinned providers, consistent tags.
- Ansible: roles with defaults and handlers, tags, idempotency, no `shell` where a module exists.
- Python: type hints, pydantic config, JSON logging, retries with backoff, no bare `except`, a test for every state transition.
- Shell: `--help`, `set -euo pipefail`, a dry-run mode where relevant.
- Every deliverable is complete and runnable; no placeholders.

## 7. Evidence rules

- A phase is done only with captured evidence (command output, screenshots, audit-log excerpts).
- Any number in docs, README or resume bullets comes from `docs/rto-rpo-report.md` or a cited official source; otherwise it is labeled an estimate.

## 8. Decisions to settle in Phase 0 (ADRs in docs/decisions/)

ADR-001 on-prem platform; ADR-002 control-plane placement; ADR-003 DR tier; ADR-004 DNS and health-check strategy behind NAT.
