variable "aws_region" {
  type        = string
  description = "Target AWS region for persistent DR resources"
  default     = "ap-southeast-2"

  validation {
    condition     = contains(["ap-southeast-2", "us-east-1", "us-west-2"], var.aws_region)
    error_message = "The aws_region must be an authorized DR region."
  }
}

variable "project_name" {
  type        = string
  description = "Project name tag and naming prefix"
  default     = "hybrid-dr"
}

variable "domain_name" {
  type        = string
  description = "Hosted zone domain name for DR service endpoints"
  default     = "dr-lab.internal"
}

variable "monthly_budget_usd" {
  type        = number
  description = "Monthly budget ceiling in USD"
  default     = 15.0

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 100
    error_message = "Monthly budget ceiling must be positive and not exceed $100."
  }
}

variable "alert_email" {
  type        = string
  description = "Email for spending alerts"
  default     = "admin@example.com"
}
