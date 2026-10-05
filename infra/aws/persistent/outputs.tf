output "account_id" {
  description = "AWS Account ID where resources were deployed"
  value       = data.aws_caller_identity.current.account_id
}

output "backup_bucket_name" {
  description = "Name of the created S3 backup bucket"
  value       = module.s3_backup.bucket_name
}

output "route53_zone_id" {
  description = "Route 53 hosted zone ID for DR services"
  value       = aws_route53_zone.primary.zone_id
}

output "ssm_fencing_parameter" {
  description = "SSM parameter path for split-brain fencing"
  value       = aws_ssm_parameter.active_site.name
}

output "backup_writer_user_name" {
  description = "IAM user for on-prem backup shipping"
  value       = module.iam.backup_writer_user_name
}

output "orchestrator_role_arn" {
  description = "IAM role ARN for DR orchestrator execution"
  value       = module.iam.orchestrator_role_arn
}
