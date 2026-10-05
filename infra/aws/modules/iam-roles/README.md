# IAM Roles Module

Least-privilege IAM user and execution roles for the Hybrid DR orchestrator and on-premises backup shipping.

## Security Controls
- `backup-writer` IAM user: Granted `PutObject` on prefix `backups/*` only. Explicit `Deny` on `DeleteObject` to guard against destructive attacks.
- `orchestrator-role`: Granted permissions to cut over Route 53 records on the specific hosted zone, update the SSM fencing flag, and describe instances.

## Inputs
| Name | Description | Type | Default | Required |
|---|---|---|---|---|
| `backup_bucket_arn` | ARN of the S3 backup bucket | `string` | n/a | yes |
| `hosted_zone_id` | Route 53 Hosted Zone ID | `string` | n/a | yes |

## Outputs
| Name | Description |
|---|---|
| `backup_writer_user_name` | Name of the IAM user for shipping backups |
| `orchestrator_role_arn` | ARN of the orchestrator IAM execution role |
