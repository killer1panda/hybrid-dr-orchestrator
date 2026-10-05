# S3 Backup Module

Encrypted, versioned S3 bucket with public access blocked and lifecycle rules to store PostgreSQL base backups and WAL segments.

## Inputs
| Name | Description | Type | Default | Required |
|---|---|---|---|---|
| `bucket_name` | Unique name for the S3 backup bucket | `string` | n/a | yes |
| `environment` | Environment name tag | `string` | `"dr-persistent"` | no |

## Outputs
| Name | Description |
|---|---|
| `bucket_name` | The name of the created S3 bucket |
| `bucket_arn` | The ARN of the created S3 bucket |
