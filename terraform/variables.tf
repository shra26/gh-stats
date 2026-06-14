variable "project_name" {
  description = "Project name used as a prefix for all resource names and the Project tag."
  type        = string
  default     = "gh-stats"
}

variable "lambda_memory" {
  description = "Lambda function memory in MB."
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds."
  type        = number
  default     = 10
}

variable "reserved_concurrency" {
  description = "Reserved concurrent executions for the Lambda function. Acts as a hard ceiling on simultaneous invokes to bound cost and GitHub API burst."
  type        = number
  default     = 25
}
