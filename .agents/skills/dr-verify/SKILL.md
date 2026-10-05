---
name: dr-verify
description: "Runs the verification gate for the current phase of the Hybrid DR project (lint, tests, plan, secret scan, cost check) and produces a Walkthrough with captured evidence. Use before declaring any phase done, or any time the user asks to verify, re-check or audit the current state."
---

# Verification gate

## Steps
1. Read docs/PROGRESS.md to find the current phase, then open that phase's skill and its verification checklist.
2. Run the checks that apply to what exists so far. Skip a check only if its target does not exist yet, and say so:
   - Terraform, for each root: `terraform fmt -check -recursive`, `terraform validate`, `tflint`.
   - Security: `trivy config` or `checkov` on `infra/`, and `gitleaks detect`.
   - Ansible: `ansible-lint`; `molecule test` where a scenario exists.
   - Python: `ruff check`, `ruff format --check`, `mypy --strict`, `pytest -q`.
   - Cost: `scripts/cost_guard.sh` and a tag query for `Project=hybrid-dr`.
   - The phase-specific checklist items.
3. If a tool is missing, report it and propose the install command; install only with the user's approval.
4. Capture real output for every check. A check you did not run is reported as not run, never as passed.
5. Produce the Walkthrough artifact in the six-part format from AGENTS.md, with a pass, fail or not-run table at the top.
6. Update docs/PROGRESS.md. Do not start fixing failures beyond the current phase's scope; list them for the user.

## Rules
- Read-only: this skill must not run `terraform apply`, `terraform destroy`, or any `aws` command that modifies resources.
- Confirm the AWS account ID against `DR_ALLOWED_ACCOUNT_ID` before any AWS read.
