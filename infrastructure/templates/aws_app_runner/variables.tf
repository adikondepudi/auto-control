variable "service_name" {
  type        = string
  description = "The name of the App Runner service."
}

variable "image_identifier" {
  type        = string
  description = "The private ECR image URI to deploy (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest)."
}

variable "aws_account_id" {
  type        = string
  description = "The AWS Account ID where the ECR repository resides."
}

variable "aws_region" {
  type        = string
  description = "The AWS Region where the ECR repository resides."
  default     = "us-east-2"
}

variable "ecr_repo_name" {
  type        = string
  description = "The name of the ECR repository."
}