# Terraform declares the parameter so the ARN is known at plan time (for the IAM policy).
# The real PAT value is NEVER stored in Terraform state -- set it out of band before deploy:
#
#   aws ssm put-parameter \
#     --name "/gh-stats/pats" \
#     --type SecureString \
#     --value "ghp_token1,ghp_token2" \
#     --overwrite \
#     --profile website-handler
#
# lifecycle.ignore_changes = [value] ensures subsequent terraform apply calls never
# overwrite the live secret with the placeholder.
resource "aws_ssm_parameter" "pats" {
  name        = "/gh-stats/pats"
  description = "Comma-separated GitHub PATs for ${var.project_name}. Set real value via aws ssm put-parameter -- do not edit here."
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_OUT_OF_BAND"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = var.project_name
  }
}
