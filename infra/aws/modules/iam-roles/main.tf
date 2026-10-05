# Backup Writer User (Used by on-prem backup shipper)
resource "aws_iam_user" "backup_writer" {
  name = "dr-onprem-backup-writer"
  tags = {
    Role         = "backup-shipper"
    AutoTeardown = "false"
  }
}

# Policy allowing PutObject and List, but explicitly forbidding DeleteObject
resource "aws_iam_user_policy" "backup_writer_policy" {
  name = "dr-backup-writer-policy"
  user = aws_iam_user.backup_writer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowListingBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = var.backup_bucket_arn
      },
      {
        Sid    = "AllowPutObject"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${var.backup_bucket_arn}/backups/*"
      },
      {
        Sid    = "DenyDeleteObject"
        Effect = "Deny"
        Action = [
          "s3:DeleteObject",
          "s3:DeleteObjectVersion"
        ]
        Resource = "${var.backup_bucket_arn}/*"
      }
    ]
  })
}

# Orchestrator Execution Role
resource "aws_iam_role" "orchestrator_role" {
  name = "dr-orchestrator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "orchestrator_policy" {
  name = "dr-orchestrator-permissions"
  role = aws_iam_role.orchestrator_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ManageRoute53Cutover"
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets",
          "route53:GetChange",
          "route53:ListResourceRecordSets"
        ]
        Resource = "arn:aws:route53:::hostedzone/${var.hosted_zone_id}"
      },
      {
        Sid    = "ManageSSMFencingFlag"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter"
        ]
        Resource = "arn:aws:ssm:ap-southeast-2:*:parameter/hybrid-dr/active-site"
      },
      {
        Sid    = "DescribeTaggedEC2"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus"
        ]
        Resource = "*"
      }
    ]
  })
}

# Data source for current account ID
data "aws_caller_identity" "current" {}

# GitHub Actions OIDC Read-Only Planning Role (No apply from CI)
resource "aws_iam_role" "github_actions_readonly" {
  name = "dr-github-actions-readonly"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
      }
      Condition = {
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:killer1panda/hybrid-dr-orchestrator:*"
        }
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    Role         = "ci-readonly-planner"
    AutoTeardown = "false"
  }
}

resource "aws_iam_role_policy" "github_actions_readonly_policy" {
  name = "dr-github-actions-readonly-policy"
  role = aws_iam_role.github_actions_readonly.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadOnlyInspection"
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "s3:Get*",
          "s3:List*",
          "route53:Get*",
          "route53:List*",
          "ssm:Get*",
          "ssm:Describe*",
          "iam:Get*",
          "iam:List*"
        ]
        Resource = "*"
      },
      {
        Sid    = "DenyMutations"
        Effect = "Deny"
        Action = [
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "s3:PutObject",
          "s3:DeleteObject",
          "route53:ChangeResourceRecordSets",
          "ssm:PutParameter",
          "iam:Create*",
          "iam:Delete*"
        ]
        Resource = "*"
      }
    ]
  })
}

