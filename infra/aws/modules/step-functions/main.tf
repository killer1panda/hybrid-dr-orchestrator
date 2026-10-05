data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_cloudwatch_log_group" "sfn_logs" {
  name              = "/aws/vendedlogs/states/${var.name_prefix}-orchestrator-${var.environment}"
  retention_in_days = 14

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-sfn-logs"
  })
}

resource "aws_iam_role" "sfn_execution" {
  name = "${var.name_prefix}-sfn-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-sfn-execution-role"
  })
}

resource "aws_iam_policy" "sfn_permissions" {
  name        = "${var.name_prefix}-sfn-policy-${var.environment}"
  description = "Permissions for Hybrid DR Step Functions execution"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:PutParameter",
          "ssm:GetParameter"
        ]
        Resource = var.fencing_parameter_arn
      },
      {
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets",
          "route53:GetChange"
        ]
        Resource = "arn:aws:route53:::hostedzone/${var.hosted_zone_id}"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_alert_topic_arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sfn_attach" {
  role       = aws_iam_role.sfn_execution.name
  policy_arn = aws_iam_policy.sfn_permissions.arn
}

resource "aws_sfn_state_machine" "orchestrator" {
  name     = "${var.name_prefix}-state-machine-${var.environment}"
  role_arn = aws_iam_role.sfn_execution.arn

  definition = file("${path.module}/asl/hybrid_dr_state_machine.json")

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-state-machine"
  })
}
