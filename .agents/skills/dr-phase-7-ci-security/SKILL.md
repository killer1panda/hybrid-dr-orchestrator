---
name: dr-phase-7-ci-security
description: "Builds Phase 7 of the Hybrid DR project: observability dashboards and alerts, the GitHub Actions CI pipeline, security scanning and a secrets and IAM review. Use when starting or resuming Phase 7 or when asked about monitoring, CI/CD, security hardening or scans."
---

# Phase 7: observability, CI/CD and security hardening

Follow the phase protocol in AGENTS.md. Prerequisites: Phases 1 to 6 complete.

## Deliverables
1. **Observability:** Prometheus with node_exporter and a blackbox exporter, Grafana dashboards provisioned as code (JSON in the repo), Alertmanager routing to the notification webhook, CloudWatch alarms plus SNS for the DR environment, structured logs. Dashboards show: site health by signal class, tunnel handshake age, backup and WAL freshness, last restore-test result, orchestrator state, drill timeline.
2. **CI** in `.github/workflows/`: terraform fmt and validate, tflint, `trivy config` or `checkov` (verify the current tool names and flags), ansible-lint, pytest, ruff, mypy, gitleaks. Plan on pull requests through GitHub OIDC with a read-only AWS role; no long-lived keys in GitHub; **no apply from CI**. Pin third-party actions to commit SHAs and add dependency update config.
3. **Security review** in `docs/security.md`: a lightweight threat model (assets, trust boundaries, threats, mitigations), a secrets inventory, an IAM review, an S3 public-access test, and residual risks (split-brain window, DNS TTL, single region, single operator).
4. Fix or time-box-waive every scan finding; waivers need an owner and an expiry date.

## Browser evidence (optional)
You may use the browser to capture screenshots or a recording of the Grafana dashboards as evidence. Read-only; ask before clicking or typing anything.

## Verification checklist (show real output)
- [ ] CI is green on a pull request (link or log excerpt).
- [ ] Scans pass, or each waiver is documented with an expiry.
- [ ] `gitleaks` is clean across the whole git history.
- [ ] Dashboards load with live data; an induced failure (stop the heartbeat) fires an alert to the webhook.
- [ ] The CI role is read-only (show a failed write attempt).
