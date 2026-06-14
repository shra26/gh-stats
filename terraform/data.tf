data "aws_route53_zone" "shravanthv" {
  name = "shravanthv.com."
}

# Reuse the existing wildcard cert already issued for shravanthv.com / *.shravanthv.com.
# Do NOT create a new aws_acm_certificate -- the cert was provisioned by my-resume/terraform.
data "aws_acm_certificate" "wildcard" {
  domain      = "shravanthv.com"
  statuses    = ["ISSUED"]
  most_recent = true
}

data "aws_caller_identity" "current" {}
