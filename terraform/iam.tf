resource "aws_iam_role" "lambda_exec" {
  name        = "${var.project_name}-lambda-exec"
  description = "Execution role for the ${var.project_name} Lambda function"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaAssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Project = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "ssm_pat" {
  name = "${var.project_name}-ssm-pat"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadPatParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = aws_ssm_parameter.pats.arn
      },
      {
        # Allow KMS decrypt for the SSM-managed default key (alias/aws/ssm).
        # Scoped to the account default SSM KMS key; safe because the Lambda
        # can only read this SSM parameter by name via the policy above.
        Sid      = "DecryptSsmKms"
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = "arn:aws:kms:us-east-1:${data.aws_caller_identity.current.account_id}:key/*"
        Condition = {
          StringLike = {
            "kms:ViaService" = "ssm.us-east-1.amazonaws.com"
          }
        }
      }
    ]
  })
}
