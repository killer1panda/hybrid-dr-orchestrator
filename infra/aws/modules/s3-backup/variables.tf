variable "bucket_name" {
  description = "Unique name for the S3 backup bucket"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dr-persistent"
}
