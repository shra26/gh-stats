output "function_url" {
  description = "Raw Lambda Function URL (AWS_IAM protected -- direct requests return 403)."
  value       = aws_lambda_function_url.this.function_url
}

output "distribution_id" {
  description = "CloudFront distribution ID (used for cache invalidations)."
  value       = aws_cloudfront_distribution.this.id
}

output "distribution_domain_name" {
  description = "CloudFront distribution domain name (e.g. d1234abcd.cloudfront.net)."
  value       = aws_cloudfront_distribution.this.domain_name
}

output "custom_domain" {
  description = "Public custom domain for the card service."
  value       = local.domain_name
}

output "sample_card_url" {
  description = "Example stats card URL to verify the deployment end-to-end."
  value       = "https://${local.domain_name}/api?username=shravanthsv&theme=tokyonight"
}
