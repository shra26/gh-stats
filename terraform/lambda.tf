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
      SSM_PAT_PARAM = aws_ssm_parameter.pats.name
    }
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${aws_lambda_function.this.function_name}"
  retention_in_days = 14

  tags = {
    Project = var.project_name
  }
}
