# Recommended agent permissions

The agent will run Terraform, Ansible and cloud CLIs on your behalf. These settings keep cloud-touching and destructive commands behind a prompt you read. They follow Antigravity's allow, ask and deny model, where conflicts resolve in the order **Deny, then Ask, then Allow**.

## 1. Pick a preset

On macOS and Linux choose **Default** (terminal commands run in a sandbox with no network, and anything needing the network or the host asks first) or **Request Review** (every command asks). Never use **Turbo** on this project. Set it under Settings > General > Permission Settings, or per project under Settings > Projects.

On Windows the setting is called **Terminal execution policy** instead of a preset; choose the option that asks before running commands. The Deny, Ask and Allow lists below still apply, with one extra action, `unsandboxed(...)`, for commands that run outside the terminal sandbox (a preview feature there). Leave the sandbox off and do not add `unsandboxed` allow rules. Write path rules in forward-slash form without a drive letter, so `<HOME>` below becomes `/Users/<you>`, because Antigravity normalizes Windows paths that way before matching. If a command rule does not seem to match in PowerShell or Command Prompt, use the `regex:` form, for example `command(regex:terraform apply.*)`.

Keep the artifact review policy on "Always ask".

## 2. Add these rules

Add them to the Agent Permissions lists in Settings (global or project level). For the Antigravity CLI, put them in `~/.gemini/antigravity-cli/settings.json`.

```json
{
  "permissions": {
    "allow": [
      "command(git status)",
      "command(git diff)",
      "command(git log)",
      "command(terraform fmt)",
      "command(terraform validate)",
      "command(tflint)",
      "command(ansible-lint)",
      "command(ruff)",
      "command(mypy)",
      "command(pytest)",
      "command(gitleaks)",
      "command(trivy config)",
      "command(checkov)"
    ],
    "ask": [
      "command(terraform init)",
      "command(terraform plan)",
      "command(terraform apply)",
      "command(terraform destroy)",
      "command(terraform import)",
      "command(terraform state)",
      "command(aws)",
      "command(ansible-playbook)",
      "command(docker)",
      "command(curl)",
      "command(qm)",
      "command(pvesh)",
      "command(wg)",
      "command(git commit)",
      "command(git push)",
      "command(make drill)",
      "command(make failback)",
      "command(make teardown)",
      "execute_url(aws.amazon.com)"
    ],
    "deny": [
      "command(rm -rf)",
      "command(sudo)",
      "command(dd)",
      "command(mkfs)",
      "command(terraform apply -auto-approve)",
      "command(terraform destroy -auto-approve)",
      "command(aws iam create-access-key)",
      "command(aws organizations)",
      "write_file(.git/)",
      "read_file(<HOME>/.aws)",
      "write_file(<HOME>/.aws)",
      "read_file(<HOME>/.ssh)",
      "write_file(<HOME>/.ssh)"
    ]
  }
}
```

Replace `<HOME>` with your home directory path.

## 3. Habits that matter more than the lists

- Prefix matching cannot catch every flag order (for example `terraform apply -var x -auto-approve`), and commands containing shell constructs such as `$(...)` fall back to Ask. That is why `terraform apply` and `terraform destroy` stay on Ask and why the always-on safety rule forbids `-auto-approve`. Read each prompt.
- When a permission card offers "always allow", do not choose it for apply, destroy, `aws` or `ansible-playbook`. Allow once.
- Move `terraform plan` to Allow only after you trust the `dr-sandbox` profile and the account-ID check.
- Re-check this file after Antigravity updates; the permission system has changed between releases.
