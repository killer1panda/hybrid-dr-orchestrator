---
trigger: glob
globs: "orchestrator/**/*.py, scripts/**/*.py, app/**/*.py"
description: "Python standards for the DR orchestrator and app: typing, config validation, logging, retries, subprocess safety, and testing every state transition."
---

# Python standards

- Python 3.11+. Full type hints; `mypy --strict` on `orchestrator/src`. Format and lint with `ruff`.
- Configuration is a pydantic model loaded from YAML and validated at startup. Invalid config fails fast with a clear message. No module-level side effects.
- The state machine is an explicit transition table (from, guard or event, to, timeout, retries, action) with pure transition functions. Side effects live behind small interfaces (Protocols) so tests can fake them. Every legal transition and every illegal one has a test.
- Inject a clock. Do not call `time.sleep` or `datetime.now` inside logic that must be tested.
- Logging is structured JSON, one event per line, with `event`, `state`, `ts_utc` and `run_id`. Never log secrets.
- Retries use exponential backoff with jitter on network and cloud calls, bounded attempts, no bare `except`, no swallowed errors. Unrecoverable failures move to `FAILED_NEEDS_HUMAN` and notify.
- Subprocesses (terraform, ansible): argument lists, `shell=False`, explicit timeout, captured output saved to the audit log. Never interpolate untrusted strings into commands.
- Idempotency: every action is safe to repeat; state is persisted atomically so a crash mid-failover resumes correctly. A leader lock prevents two orchestrators acting at once.
- Real provisioning is off by default (dry-run on); enabling it needs an explicit flag.
- Gate: `pytest -q`, `ruff check`, `ruff format --check` and `mypy --strict` all shown passing.
