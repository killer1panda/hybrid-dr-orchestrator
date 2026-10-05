# AWS Step Functions State Machine Module

Manages the enterprise cloud-native Disaster Recovery State Machine orchestrated via AWS Step Functions.

## Inputs

| Name | Type | Description | Default |
|---|---|---|---|
| `name_prefix` | `string` | Prefix for Step Functions resource names | `"hybrid-dr"` |
| `environment` | `string` | Target deployment environment | `"dr"` |
| `fencing_parameter_arn` | `string` | ARN of the SSM active-site fencing parameter | Required |
| `hosted_zone_id` | `string` | Route 53 hosted zone ID for DNS cutover | Required |
| `backup_bucket_arn` | `string` | ARN of the S3 disaster recovery backup bucket | Required |
| `sns_alert_topic_arn` | `string` | ARN of the SNS topic for disaster alerts | Required |
| `tags` | `map(string)` | Resource tags | `{}` |

## Outputs

| Name | Description |
|---|---|
| `state_machine_arn` | ARN of the Disaster Recovery Step Functions state machine |
| `state_machine_id` | ID of the Disaster Recovery Step Functions state machine |
| `execution_role_arn` | ARN of the IAM role used by Step Functions |
