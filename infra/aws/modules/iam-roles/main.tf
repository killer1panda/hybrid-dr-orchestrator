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
