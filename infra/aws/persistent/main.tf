terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  backend "s3" {
    bucket       = "hybrid-dr-backups-758579869433-ap-southeast-2"
    key          = "state/persistent/terraform.tfstate"
    region       = "ap-southeast-2"
    profile      = "dr-sandbox"
    use_lockfile = true
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "dr-sandbox"

  default_tags {
    tags = {
      Project      = var.project_name
      Environment  = "persistent"
      AutoTeardown = "false"
      ManagedBy    = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id  = data.aws_caller_identity.current.account_id
  bucket_name = "${var.project_name}-backups-${local.account_id}-${var.aws_region}"
}

module "s3_backup" {
  source      = "../modules/s3-backup"
  bucket_name = local.bucket_name
}

resource "aws_route53_zone" "primary" {
  name    = var.domain_name
  comment = "Private/Internal DR Test Hosted Zone"

  tags = {
    Name = var.domain_name
  }
}

module "iam" {
  source            = "../modules/iam-roles"
  backup_bucket_arn = module.s3_backup.bucket_arn
  hosted_zone_id    = aws_route53_zone.primary.zone_id
}

# Fencing Parameter Store
resource "aws_ssm_parameter" "active_site" {
  name        = "/hybrid-dr/active-site"
  description = "Active authoritative datacenter site (onprem or AWS)"
  type        = "String"
  value       = "onprem"
  overwrite   = true

  tags = {
    Role = "split-brain-fencing"
  }
}

# Budget Alert
resource "aws_sns_topic" "budget_alerts" {
  name = "dr-budget-spend-alerts"
}

resource "aws_budgets_budget" "cost_ceiling" {
  name              = "hybrid-dr-monthly-budget"
  budget_type       = "COST"
  limit_amount      = tostring(var.monthly_budget_usd)
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2026-10-01_00:00"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
