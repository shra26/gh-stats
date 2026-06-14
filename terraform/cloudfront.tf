locals {
  lambda_origin_id = "${var.project_name}-lambda-origin"
}

# OAC for Lambda Function URLs (origin_type = "lambda", signing = always/sigv4).
# This is the Lambda equivalent of the S3 OAC in besa-home/terraform/cloudfront.tf.
resource "aws_cloudfront_origin_access_control" "lambda" {
  name                              = "${var.project_name}-lambda-oac"
  description                       = "OAC for ${var.project_name} Lambda Function URL"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Cache policy: key on path + whitelisted query params only (no headers, no cookies).
# Whitelist prevents cache-busting via arbitrary params while covering all known card params.
# min_ttl=0 lets the origin set short TTLs (e.g. max-age=600 for error cards).
# max_ttl=864000 accommodates the longest per-card TTL (pin / top-langs at 864000 s).
resource "aws_cloudfront_cache_policy" "this" {
  name    = "${var.project_name}-cache-policy"
  comment = "Cache by path + whitelisted query params; no headers or cookies forwarded"

  min_ttl     = 0
  default_ttl = 86400
  max_ttl     = 864000

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true

    query_strings_config {
      query_string_behavior = "whitelist"
      query_strings {
        items = [
          "username",
          "repo",
          "id",
          "theme",
          "hide",
          "hide_title",
          "hide_rank",
          "hide_border",
          "show",
          "show_icons",
          "include_all_commits",
          "commits_year",
          "card_width",
          "line_height",
          "title_color",
          "ring_color",
          "icon_color",
          "text_color",
          "text_bold",
          "bg_color",
          "border_color",
          "border_radius",
          "number_format",
          "number_precision",
          "rank_icon",
          "exclude_repo",
          "custom_title",
          "locale",
          "disable_animations",
          "layout",
          "langs_count",
          "size_weight",
          "count_weight",
          "hide_progress",
          "stats_format",
          "show_owner",
          "description_lines_count",
          "api_domain",
          "display_format",
          "cache_seconds",
        ]
      }
    }

    headers_config {
      header_behavior = "none"
    }

    cookies_config {
      cookie_behavior = "none"
    }
  }
}

# Origin request policy: forward all query strings to the origin so the Lambda
# receives params that may not be in the cache key whitelist (for future-proofing).
# Never forward Host or cookies -- that breaks the Function URL and shatters the cache.
resource "aws_cloudfront_origin_request_policy" "this" {
  name    = "${var.project_name}-origin-request-policy"
  comment = "Forward all query strings to Lambda; no headers or cookies"

  query_strings_config {
    query_string_behavior = "all"
  }

  headers_config {
    header_behavior = "none"
  }

  cookies_config {
    cookie_behavior = "none"
  }
}

resource "aws_cloudfront_distribution" "this" {
  enabled     = true
  comment     = "${var.project_name} Lambda card renderer"
  price_class = "PriceClass_All"
  aliases     = [local.domain_name]
  web_acl_id  = aws_wafv2_web_acl.this.arn

  # Strip "https://" prefix and trailing "/" from the Function URL to get a bare hostname.
  # replace() is applied twice: first remove the scheme, then remove any trailing slash.
  origin {
    origin_id                = local.lambda_origin_id
    domain_name              = replace(replace(aws_lambda_function_url.this.function_url, "https://", ""), "/", "")
    origin_access_control_id = aws_cloudfront_origin_access_control.lambda.id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.lambda_origin_id

    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    cache_policy_id          = aws_cloudfront_cache_policy.this.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.this.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = data.aws_acm_certificate.wildcard.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Project = var.project_name
  }
}
