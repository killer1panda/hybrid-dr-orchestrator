output "bucket_name" {
  description = "The name of the S3 backup bucket"
  value       = aws_s3_bucket.backup.id
}

output "bucket_arn" {
  description = "The ARN of the S3 backup bucket"
  value       = aws_s3_bucket.backup.arn
}
