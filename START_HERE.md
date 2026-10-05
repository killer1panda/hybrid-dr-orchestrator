# Start here: Antigravity starter kit for the Hybrid DR Orchestrator

This folder is the project repo root. Open this folder itself (not its parent) as the workspace in Antigravity.

## What is in the kit

| Path | What it does |
|---|---|
| `AGENTS.md` | Always-on project instructions: goal, phase list, phase protocol |
| `docs/project-spec.md` | Full specification the agent reads before planning |
| `.agents/rules/` | Scoped rules: safety and spend (always on); Terraform, Ansible, Python (by file type); docs (agent decides) |
| `.agents/skills/` | One skill per phase, plus `/dr-verify` and `/dr-teardown` |
| `docs/PROGRESS.md` | Status, decisions and spend ledger the agent keeps updated |
| `docs/PERMISSIONS.md` | Recommended allow, ask and deny rules for the agent's terminal |
| `KICKOFF_PROMPT.md` | The one prompt you paste to begin |

## Setup (about 10 minutes)

1. Unzip, then run `git init` in the folder.
2. Open the folder in Antigravity (File > Open Folder).
3. Check it loaded: in the agent panel ask "Which rules and skills are installed?" You should see 5 rules and 11 skills. You can also open Customizations from the agent panel menu.
4. Apply the settings in `docs/PERMISSIONS.md` before the agent touches a terminal. Keep the artifact review policy on "Always ask" so you approve every plan.
5. Do not create AWS resources yet. Phase 0 walks you through the AWS sandbox profile `dr-sandbox` and the `DR_ALLOWED_ACCOUNT_ID` variable.
6. Fill in the brackets in `KICKOFF_PROMPT.md` and paste it into a new conversation.

## Driving the project

- One phase at a time: `/dr-phase-1-onprem`, `/dr-phase-2-aws-foundation`, and so on. Each phase starts with an Implementation Plan you approve and ends with a Walkthrough that contains evidence.
- After every drill run `/dr-teardown`. At any time run `/dr-verify`.
- Resuming later: start a new conversation and say "Read AGENTS.md and docs/PROGRESS.md, then continue."
- If slash commands do not list the skills, type "use the dr-phase-1-onprem skill".
- Parallel agents in Agent Manager are fine only on separate folders (for example infra/ and ansible/ in Phase 4). Never let two agents edit the same file.

## Good to know

- Files in `.agents/rules/` must start with YAML frontmatter and a lowercase `trigger` (`always_on`, `model_decision`, `glob` or `manual`). Otherwise Antigravity silently ignores them. Only files directly inside that folder are read.
- Each rule file is capped at 24 KB, and always-on rules share a 20,000-token budget. This kit uses a small fraction.
- Older guides use `.agent/` and workflows. Current Antigravity uses `.agents/` and skills, and workflows are scheduled to be retired on November 1, 2026.
- On Windows the permission settings differ slightly: a Terminal execution policy instead of presets, and path rules written without a drive letter. The allow, ask and deny lists still work. See `docs/PERMISSIONS.md`.
- Antigravity changes quickly. If something here does not match your version, trust the in-app Customizations panel and ask the agent to adapt the file.

## Cost reality check

The persistent AWS layer (state, backups, DNS zone, budget) is small but not zero; a Route 53 hosted zone is billed monthly. Each drill costs a few EC2 hours plus data transfer. The agent must show an estimate before every apply, and you approve each one.
