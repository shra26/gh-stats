# WAF Web ACL must be in us-east-1 for CloudFront (scope = CLOUDFRONT).
# The provider is already configured for us-east-1 in providers.tf.
resource "aws_wafv2_web_acl" "this" {
  name        = "${var.project_name}-waf"
  description = "WAF for ${var.project_name} CloudFront distribution"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # Rule 1: rate limit per source IP to bound amplification / denial-of-wallet.
  # >300 requests per 5-minute window from a single IP triggers a block.
  rule {
    name     = "RateLimitPerIp"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 300
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-rate-limit-per-ip"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: block known malicious IPs (AWS-curated reputation list).
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesAmazonIpReputationList"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-ip-reputation"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: block anonymous / VPN / Tor exit nodes.
  rule {
    name     = "AWSManagedRulesAnonymousIpList"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesAnonymousIpList"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-anonymous-ip"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: block known bad inputs (log4j, SQLi patterns, etc.).
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-known-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Project = var.project_name
  }
}
