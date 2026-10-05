---
trigger: always_on
description: "Hard safety and cloud-spend guardrails for the Hybrid DR project: approvals for apply and destroy, credential handling, chaos-tooling limits, tagging and teardown."
---

# Safety and spend guardrails

These are invariants. If a task seems to require breaking one, stop and ask the user.

## Cloud changes need approval
- Never run `terraform apply`, `terraform destroy`, `terraform import`, `terraform state` changes, `aws` commands that create, modify or delete resources, or `ansible-playbook` against real hosts without explicit approval in the current turn.
- Before any apply, show the `terraform plan` summary (adds, changes, destroys) and an estimated cost for that run. Never use `-auto-approve`.
- Before any AWS call, run `aws sts get-caller-identity` and confirm the account ID equals the env var `DR_ALLOWED_ACCOUNT_ID`. If it is unset or different, stop. Use only the named profile `dr-sandbox`. Never use root credentials.

## Credentials and secrets
- Never read, print, log, echo or commit credentials, tokens, private keys, `.env` files, `*.tfstate`, or `*.tfvars` that contain secrets. Never paste a secret into chat or into a file.
- Secrets live in environment variables, SOPS-encrypted files, Ansible Vault, or AWS SSM Parameter Store / Secrets Manager. Commit only `*.example` templates.
- `.gitignore` must be in place before the first commit. Run `gitleaks` before proposing any commit.

## Cost control
- Tag every AWS resource: `Project=hybrid-dr`, `Environment`, `Owner`, and `AutoTeardown=true` (ephemeral) or `false` (persistent). Use provider `default_tags`.
- Prefer small, single-instance, free-tier-eligible designs. Avoid NAT gateways, load balancers, multi-AZ databases and customer-managed KMS keys unless the user approves the monthly cost in writing.
- Nothing billable is created until `make teardown` and the budget alarm exist.
- Record every drill's estimated and actual cost in the spend ledger in docs/PROGRESS.md.
- Ephemeral resources (the DR environment) and persistent resources (state, backups, DNS zone, budget) are separate Terraform roots. Teardown must never touch the persistent root or the backup bucket.

## Chaos and destructive commands
- Chaos tooling may only target VMs and interfaces listed in `lab-inventory.yml`. It must support `--dry-run`, require `--confirm`, and refuse to touch the host's own network interfaces, the user's other VMs, or anything outside the lab bridge.
- `rm -rf`, disk or partition tools, `qm destroy`, `pvesm`, `dd`, `mkfs` and `sudo` need approval and a dry run first.

## Behavior
- If a command is refused or fails twice, stop and report. Do not retry with broader permissions or look for a route around a block.
- Do not push to a remote, open pull requests, or change cloud or IAM settings on your own initiative.
