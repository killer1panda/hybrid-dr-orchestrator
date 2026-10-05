---
trigger: glob
globs: "**/*.tf, **/*.tfvars, **/*.tftest.hcl"
description: "Terraform standards for the Hybrid DR project: structure, version pinning, validation, tagging, and persistent versus ephemeral separation."
---

# Terraform standards

- **Layout:** reusable code in `infra/aws/modules/<name>/`. Root configurations: `infra/aws/persistent/` (state, IAM, backup bucket, DNS zone, budget; never destroyed by teardown) and `infra/aws/envs/dr/` (the ephemeral DR environment). On-prem lives in `infra/onprem/`.
- Every module has `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` and a short README listing inputs and outputs.
- Pin `required_version` and every provider with a pessimistic constraint (`~>`) and commit `.terraform.lock.hcl`. Look up current versions in the registry; do not guess them.
- Variables are typed and described, with `validation` blocks where a bad value would be costly (region allow-list, instance-type allow-list, CIDR format). No hard-coded account IDs, regions, AMI IDs or IPs; resolve AMIs through SSM parameters or data sources.
- Tags come from provider `default_tags` (see the safety rule) plus a per-resource `Name`.
- Mark sensitive variables and outputs `sensitive = true`. Commit `*.tfvars.example`, never real `*.tfvars` with secrets.
- Backup bucket: versioning on, default encryption on, public access blocked, lifecycle expiry rules, `lifecycle { prevent_destroy = true }`.
- Prefer `for_each` over `count` for named resources. Do not use `local-exec` for work Ansible should do.
- Quality gate before declaring done: `terraform fmt -check -recursive`, `terraform validate`, `tflint`, and a security scan (`trivy config` or `checkov`). Show the output.
- Summarize `terraform plan` (adds, changes, destroys) for the user before any apply request.
