variable "name_prefix" {
  type        = string
  description = "Prefix for Step Functions resource names"
  default     = "hybrid-dr"
}

variable "environment" {
  type        = string
  description = "Target deployment environment"
  default     = "dr"
}

variable "fencing_parameter_arn" {
  type        = string
  description = "ARN of the SSM active-site fencing parameter"
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 hosted zone ID for DNS cutover"
}

variable "backup_bucket_arn" {
  type        = string
  description = "ARN of the S3 disaster recovery backup bucket"
}

variable "sns_alert_topic_arn" {
  type        = string
  description = "ARN of the SNS topic for disaster alerts"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
