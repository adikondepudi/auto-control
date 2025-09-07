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

# --- New Exceptions for Phase 2 ---

class DockerError(AutoDeployerException):
    """Base exception for Docker-related operations."""
    pass

class ECRAuthError(DockerError):
    """Raised when authentication with AWS ECR fails."""
    pass

class DockerBuildError(DockerError):
    """Raised when the 'docker build' command fails."""
    pass

class DockerPushError(DockerError):
    """Raised when the 'docker push' command fails."""
    pass