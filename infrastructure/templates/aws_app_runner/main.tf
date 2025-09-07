provider "aws" {
  region = "us-east-1" # Or your desired region
}

resource "aws_apprunner_service" "main" {
  service_name = var.service_name

  source_configuration {
    image_repository {
      image_identifier      = var.image_identifier
      image_repository_type = "ECR_PUBLIC" # Simplified for this MVP
      image_configuration {
        port = "8080"
      }
    }
    auto_deployments_enabled = false # Keep it simple, no auto-deployments
  }

  tags = {
    ManagedBy = "AutoDeployer"
  }
}

output "service_url" {
  description = "The publicly accessible URL of the App Runner service."
  value       = aws_apprunner_service.main.service_url
}