---
trigger: glob
globs: "ansible/**/*.yml, ansible/**/*.yaml"
description: "Ansible standards for the Hybrid DR project: roles, idempotency, secrets handling and check-mode discipline."
---

# Ansible standards

- One role per concern under `ansible/roles/` (common, nginx, app, postgres, wireguard, node_exporter). Each has `defaults/`, `tasks/`, `handlers/`, `meta/` and, where useful, `templates/` and a Molecule scenario.
- Use fully qualified module names (`ansible.builtin.*`, `community.postgresql.*`). Use a module instead of `shell` or `command`; when unavoidable, add `changed_when` / `failed_when` and `creates` / `removes`.
- Idempotent: a second run must report `changed=0`. Show that in the evidence.
- Always run `--check --diff` first. The real run needs approval under the safety rule.
- Secrets: Ansible Vault or SSM lookups only. No plaintext secrets in vars, templates or logs; use `no_log: true` on tasks that handle them.
- Inventories live under `ansible/inventories/<site>/`. The AWS inventory is generated from Terraform outputs and never hand-edited.
- Name every task and tag tasks so phases can be re-run in part.
- Gate: `ansible-lint` (production profile) and `molecule test` where a scenario exists.
