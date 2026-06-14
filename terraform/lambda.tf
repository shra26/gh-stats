data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/build/function.zip"
}

resource "aws_lambda_function" "this" {
  function_name = "${var.project_name}-handler"
  description   = "GitHub Readme Stats card renderer"

  runtime       = "python3.12"
  architectures = ["arm64"]
  handler       = "handler.handler"

  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  memory_size                    = var.lambda_memory
  timeout                        = var.lambda_timeout
  reserved_concurrent_executions = var.reserved_concurrency

  role = aws_iam_role.lambda_exec.arn

  environment {
    variables = {
      # Name of the SSM SecureString parameter holding the comma-separated PAT list.
      # The actual secret value is never stored in Terraform state.
      SSM_PAT_PARAM = aws_ssm_parameter.pats.name

      # Optional: comma-separated GitHub usernames allowed by the allowlist check.
      # Set this after initial deploy: aws ssm put-parameter or a tfvars override.
      # GH_WHITELIST = ""
    }
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_lambda_function_url" "this" {
  function_name      = aws_lambda_function.this.function_name
  authorization_type = "AWS_IAM"
}

# Grant CloudFront OAC permission to invoke the Function URL via SigV4.
# References aws_cloudfront_distribution.this.arn (computed attr) -- Terraform resolves
# the ordering automatically; no cycle because the distribution only references the
# function URL host string, not this permission resource.
resource "aws_lambda_permission" "cloudfront" {
  statement_id  = "AllowCloudFrontInvokeFunctionUrl"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.this.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.this.arn
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${aws_lambda_function.this.function_name}"
  retention_in_days = 14

  tags = {
    Project = var.project_name
  }
}
