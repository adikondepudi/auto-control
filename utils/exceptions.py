class AutoDeployerException(Exception):
    """Base exception class for all custom exceptions in the application."""
    pass

class RepoAnalysisError(AutoDeployerException):
    """Raised when repository analysis fails."""
    pass

class ContainerizationError(AutoDeployerException):
    """Raised when containerization (e.g., Dockerfile generation) fails."""
    pass

class TerraformError(AutoDeployerException):
    """Raised when a Terraform command fails."""
    pass