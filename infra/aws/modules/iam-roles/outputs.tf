output "backup_writer_user_name" {
  description = "Name of the IAM user for shipping backups"
  value       = aws_iam_user.backup_writer.name
}

output "orchestrator_role_arn" {
  description = "ARN of the orchestrator IAM execution role"
  value       = aws_iam_role.orchestrator_role.arn
}
