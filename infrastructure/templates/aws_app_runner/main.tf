provider "aws" {
  region = var.aws_region
}

# IAM Role for App Runner to access ECR
resource "aws_iam_role" "apprunner_ecr_access" {
  name = "${var.service_name}-ecr-access-role"

  # Trust policy allowing App Runner to assume this role
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    ManagedBy = "AutoDeployer"
  }
}

# IAM Policy defining the permissions needed to pull from ECR
resource "aws_iam_policy" "ecr_access_policy" {
  name        = "${var.service_name}-ecr-access-policy"
  description = "Grants App Runner access to a specific ECR repository"

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:DescribeImages",
          "ecr:GetAuthorizationToken"
        ]
        Resource = "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.ecr_repo_name}"
      },
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      }
    ]
  })
}

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "apprunner_ecr_attach" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = aws_iam_policy.ecr_access_policy.arn
}

# App Runner Service configured for Private ECR
resource "aws_apprunner_service" "main" {
  service_name = var.service_name

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }
    image_repository {
      image_identifier      = var.image_identifier
      image_repository_type = "ECR"
      image_configuration {
        port = "8080"
      }
    }
    auto_deployments_enabled = false
  }

  depends_on = [
    aws_iam_role.apprunner_ecr_access,
    aws_iam_role_policy_attachment.apprunner_ecr_attach,
  ]

  tags = {
    ManagedBy = "AutoDeployer"
  }
}

output "service_url" {
  description = "The publicly accessible URL of the App Runner service."
  value       = aws_apprunner_service.main.service_url
}