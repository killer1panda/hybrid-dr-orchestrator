---
name: dr-phase-2-aws-foundation
description: "Builds Phase 2 of the Hybrid DR project: the persistent AWS layer with remote Terraform state, least-privilege IAM, encrypted backup bucket, Route 53 zone, fencing parameter and budget alarm. Use when starting or resuming Phase 2 or when asked to set up the AWS foundation. Creates nothing expensive."
---

# Phase 2: AWS foundation (persistent layer)

Follow the phase protocol in AGENTS.md. Prerequisites: Phase 0 approved, the `dr-sandbox` profile configured, `DR_ALLOWED_ACCOUNT_ID` exported. This phase builds only `infra/aws/persistent/`; the ephemeral DR root comes in Phase 4.

## Preflight (every session)
Run `aws sts get-caller-identity` with the `dr-sandbox` profile and confirm the account ID equals `DR_ALLOWED_ACCOUNT_ID`. If not, stop.

## Deliverables
1. **Remote state.** Check the current Terraform S3 backend documentation for the recommended locking method (native lockfile versus a legacy DynamoDB table) and use that. Handle the bootstrap chicken-and-egg: first apply with local state, then migrate. Document it in the runbook.
2. **Backup bucket** (module `s3-backup`): versioning, default encryption, public access blocked, lifecycle expiry, `prevent_destroy`. Prefer SSE-S3 or the AWS-managed key; a customer-managed KMS key adds a monthly cost and needs the user's written approval.
3. **IAM, least privilege, one role or user per job:**
   - backup writer (used by on-prem): `PutObject` and list on the backup prefix only; cannot delete.
   - terraform provisioner for the DR root, scoped by region and tags where possible.
   - orchestrator: update records in one hosted zone, read and write the fencing parameter, describe and start only tagged resources.
   - Credentials for on-prem: compare IAM Roles Anywhere (no long-lived keys, more setup) with a scoped IAM user plus a rotation runbook. Recommend one, document the trade-off.
4. **Route 53** hosted zone for the chosen domain or test zone (note its small monthly cost).
5. **Fencing flag** as an SSM parameter (for example `/hybrid-dr/active-site`, default `onprem`).
6. **Budget** with alerts at 50, 80 and 100 percent of the user's ceiling to an SNS topic and email.
7. `scripts/cost_guard.sh`: lists billable resources by tag `Project=hybrid-dr`, supports `--help`. `Makefile` target `teardown` (calls the /dr-teardown logic; ephemeral root only).
8. `docs/security.md` first section: IAM design and the credential decision.

## Approvals
Every `terraform apply` and every state migration needs approval with the plan summary and a cost estimate.

## Verification checklist (show real output)
- [ ] `fmt`, `validate`, `tflint`, and `trivy config` or `checkov` pass.
- [ ] `terraform plan` is clean after apply (no drift).
- [ ] Upload and download through the backup-writer identity works.
- [ ] Negative tests: the writer cannot delete objects and cannot write outside its prefix.
- [ ] `prevent_destroy` blocks a destroy of the bucket.
- [ ] The budget and SNS subscription exist and the email was confirmed.
- [ ] A tag-based resource listing shows only the expected persistent resources.
