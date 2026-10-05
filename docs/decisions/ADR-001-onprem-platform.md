# ADR-001: Simulated On-Premises Platform (Proxmox VE vs OpenStack vs Lite Mode)
- Status: accepted
- Date: 2026-10-05

## Context
We require a simulated private cloud environment hosting a 3-tier workload (Nginx, FastAPI, PostgreSQL) and a WireGuard VPN endpoint on macOS.

## Options
| Option | Pros | Cons | Cost & Effort |
|---|---|---|---|
| 1. Proxmox VE | Native VM lifecycles, REST API, cloud-init | High RAM footprint, requires nested virt | Free; Medium effort |
| 2. OpenStack | Enterprise standard | Prohibitive RAM (>=32GB), fragile setup | Free; Excessive effort |
| 3. Lite Mode (Docker Compose) | Zero overhead, native macOS, fast startup (<15s) | Shared OS kernel | Free; Low effort |

## Decision
We adopt **Lite Mode (Docker Compose) as primary local runner**, with Proxmox VE compatibility maintained via Ansible.
1. Footprint: OpenStack exceeds single-workstation memory budgets.
2. Setup Effort: Docker Compose boots in seconds.
3. API Surface: Proxmox and Compose expose simple, reliable lifecycle commands.
4. Portability: Lite mode runs identically across macOS Apple Silicon and Intel.
5. Interview Reusability: Exercises identical network and failure semantics.
