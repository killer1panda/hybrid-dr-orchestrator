---
name: dr-teardown
description: "Safely tears down the billable AWS resources of the Hybrid DR project (the ephemeral DR environment) without touching backups, state or the persistent layer, then proves nothing billable remains. Use after every drill, when the user asks to stop costs, clean up or destroy the DR environment, or at project end."
---

# Teardown of the ephemeral DR environment

## Steps
1. **Preflight.** Run `aws sts get-caller-identity` with the `dr-sandbox` profile and confirm the account ID equals `DR_ALLOWED_ACCOUNT_ID`. If not, stop.
2. **Inventory.** List resources tagged `Project=hybrid-dr` and `AutoTeardown=true` (resource tagging API) and run `terraform state list` in `infra/aws/envs/dr`. Reconcile the two lists and flag anything tagged but not in state.
3. **Plan.** Run `terraform plan -destroy` in `infra/aws/envs/dr` only. Summarize the counts and types to the user.
4. **Approval.** Ask the user to approve explicitly. No `-auto-approve`.
5. **Destroy** in `infra/aws/envs/dr` only. If it fails, do not force it: show the error, then list the orphaned resources for the user to delete.
6. **Prove it.** Re-run the tag query and check the usual cost leaks: EC2 instances, EBS volumes and snapshots, Elastic IPs, network interfaces, NAT gateways, load balancers, Route 53 health checks. Confirm the DNS record points where the user expects.
7. **Report** what remains and its recurring cost (the persistent layer: for example the hosted zone), and add the drill's actual cost to the spend ledger in docs/PROGRESS.md.

## Hard limits
- Never destroy `infra/aws/persistent` or the backup bucket. Only if the user explicitly says "tear down everything": list the backups that would be lost, then require the user to type the bucket name before proceeding.
- Never delete resources that are not tagged `Project=hybrid-dr`.
