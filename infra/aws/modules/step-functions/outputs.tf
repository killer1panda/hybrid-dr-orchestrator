output "state_machine_arn" {
  value       = aws_sfn_state_machine.orchestrator.arn
  description = "ARN of the Disaster Recovery Step Functions state machine"
}

output "state_machine_id" {
  value       = aws_sfn_state_machine.orchestrator.id
  description = "ID of the Disaster Recovery Step Functions state machine"
}

output "execution_role_arn" {
  value       = aws_iam_role.sfn_execution.arn
  description = "ARN of the IAM role used by Step Functions"
}
