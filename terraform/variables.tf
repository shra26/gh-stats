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
  description = "Reserved concurrent executions for the Lambda function (-1 = no reservation, uses unreserved pool). Set to a positive value to cap simultaneous invokes."
  type        = number
  default     = -1
}
