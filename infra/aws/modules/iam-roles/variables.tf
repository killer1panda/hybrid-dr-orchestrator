variable "backup_bucket_arn" {
  description = "ARN of the S3 backup bucket"
  type        = string
}

variable "hosted_zone_id" {
  description = "Route 53 Hosted Zone ID"
  type        = string
}
