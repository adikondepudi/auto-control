variable "service_name" {
  type        = string
  description = "The name of the App Runner service."
}

variable "image_identifier" {
  type        = string
  description = "The ECR image URI to deploy."
}