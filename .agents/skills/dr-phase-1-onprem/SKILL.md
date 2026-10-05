---
name: dr-phase-1-onprem
description: "Builds Phase 1 of the Hybrid DR project: the simulated on-prem site (Proxmox VE or lite-mode KVM/Vagrant) with web, app and db VMs and the sample 3-tier app. Use when starting or resuming Phase 1, or when asked to set up the on-prem lab."
---

# Phase 1: simulated on-prem site

Follow the phase protocol in AGENTS.md. Read docs/project-spec.md and the accepted ADR-001 first. If Phase 0 outputs are missing, tell the user to run /dr-phase-0-plan.

## Deliverables
1. `docs/runbook-onprem-setup.md`: exact steps for the human-only parts (installing Proxmox or the lite-mode hypervisor, enabling nested virtualization, creating a least-privilege API token), with what the user should see at each step. You cannot click through an installer.
2. `infra/onprem/`: Terraform for three VMs (web, app, db) from a cloud-init template on an isolated lab bridge with static IPs. Use the actively maintained Proxmox provider and verify its current name and version in the registry. In lite mode, provide the equivalent Vagrantfile or libvirt definition.
3. A script that builds the cloud-init template image, with `--help` and `--dry-run`.
4. `ansible/` roles `common`, `nginx`, `app`, `postgres`, `node_exporter` and `playbooks/site.yml`. Inventory is generated from Terraform outputs.
5. `app/`: FastAPI service with `GET /healthz` (verifies the DB connection end to end), CRUD on `items`, a Dockerfile, and `app/rpo_probe.py`, a writer that inserts a monotonically increasing counter and a UTC timestamp into table `rpo_probe` once per second. Phase 6 measures RPO with it.
6. `lab-inventory.yml`: the allow-list of VM names and IPs that chaos tooling may touch.
7. `Makefile` targets `lab-up`, `lab-down`, `lab-status`.

## Approvals
`terraform apply`, non-check `ansible-playbook`, and any Proxmox CLI (`qm`, `pvesh`) need approval each time. Use the browser only for read-only screenshots of the Proxmox UI as evidence, and ask before clicking anything.

## Verification checklist (show real output)
- [ ] `terraform fmt -check`, `validate` and `plan` are clean; the plan summary was shown before apply.
- [ ] `ansible-playbook --check --diff` was reviewed, then a real run succeeded.
- [ ] A second playbook run reports `changed=0`.
- [ ] `curl http://<web-ip>/healthz` returns 200 and reports the DB connected.
- [ ] An item can be created and read back through Nginx.
- [ ] `rpo_probe` rows are accumulating.
- [ ] `make lab-down` then `make lab-up` rebuilds the lab from nothing.
- [ ] `gitleaks` finds no secrets.

## Failure modes to pre-empt
Nested virtualization disabled; template VM missing cloud-init; guest agent not installed so IPs are not reported; lab bridge without NAT so VMs cannot reach package mirrors; clock skew breaking TLS.
