# Kickoff prompt

Open this folder as the workspace in Antigravity, fill in the brackets, then paste everything below the line into a new conversation.

---

Read AGENTS.md and docs/project-spec.md, then run the dr-phase-0-plan skill.

My environment (use these answers and ask only about what is missing):
- Host OS, RAM, CPU virtualization / nested virtualization: [...]
- On-prem lab preference: [Proxmox nested / Proxmox bare metal / lite mode / not sure]
- AWS: [new account / existing], plan [credits / legacy free tier / not sure], region [...], monthly cost ceiling [...]
- Domain: [I own one / none]
- GitHub repo: [name, public or private]
- Notifications: [Slack / Discord / email]
- Time: [hours per week], target finish [date]
- Already installed: [Terraform, Ansible, Docker, Python versions]

Rules of engagement:
- Phase 0 writes docs only: no Terraform, no AWS API calls, no installs. Looking facts up in official docs is fine.
- Produce an Implementation Plan artifact first and wait for my approval.
- Ask all clarifying questions in one batch, with a recommended default for each.
- After Phase 0, stop. I will start each following phase with its slash command.
