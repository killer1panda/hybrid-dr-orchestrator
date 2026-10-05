---
name: dr-phase-5-orchestrator
description: "Builds Phase 5 of the Hybrid DR project: the Python orchestrator with multi-signal monitoring, external quorum, an explicit state machine, action modules, fencing, audit log, notifier and unit tests. Use when starting or resuming Phase 5 or when asked to build or test the orchestrator."
---

# Phase 5: the orchestrator

Follow the phase protocol in AGENTS.md and the Python standards rule. Prerequisites: Phase 4 proven by hand; ADR-002 (control-plane placement) accepted.

## Layout (`orchestrator/src/hybrid_dr/`)
- `config.py`: pydantic models and YAML loading; `config.example.yaml` ships with real defaults and dry-run ON.
- `interfaces.py`: Protocols for every side effect. Commit this first.
- `signals/`: http, tcp, proxmox, heartbeat, tunnel, external_probe.
- `quorum.py`: failure only when N consecutive failures span at least two independent signal classes AND the external vantage agrees AND maintenance mode is off. Cooldown against flapping.
- `state_machine.py`: explicit transition table from docs/architecture.md; pure functions; persisted state with atomic writes; leader lock so two orchestrators cannot act at once.
- `actions/`: terraform, ansible, dns, restore, smoke, fencing. Subprocess wrapper with timeout, no shell, output captured to audit.
- `notifier.py`, `audit.py` (JSON lines locally plus upload to S3; monotonic timestamps on every event), `cli.py` with `run`, `status`, `drill --dry-run`, `failback`.
- `orchestrator/Dockerfile`, `Makefile` targets `orch-test`, `orch-run`.

## Safety defaults
- Real provisioning needs an explicit flag such as `--i-understand-this-provisions-aws`; otherwise dry-run.
- Any unrecoverable step ends in `FAILED_NEEDS_HUMAN` with a notification.
- Fencing is set before DNS cutover (see project-spec section 4.4).

## Parallel work
Only after `interfaces.py` is committed, the work may split into signals plus quorum, state machine, and actions on separate folders. Never let two agents edit the same file.

## Verification checklist (show real output)
- [ ] `pytest -q`, `ruff check`, `ruff format --check`, `mypy --strict` all pass.
- [ ] Tests cover every legal transition, every illegal transition, the quorum truth table, retries and timeouts with a fake clock.
- [ ] AWS interactions are tested with a mocking library, not the real account.
- [ ] A dry-run drill against fixture signals produces the expected audit sequence (show it).
- [ ] Crash test: kill the process mid-failover in a simulated run, restart, and show it resumes without repeating completed steps.
- [ ] A false-alarm test: a single failing signal class never triggers failover.
