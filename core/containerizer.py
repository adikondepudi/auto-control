import os
import base64
import boto3
import docker
from botocore.exceptions import ClientError
from utils import exceptions
from utils.logger import log

class Containerizer:
    """
    Handles the generation of containerization files, like Dockerfiles.
    """

    # --- THE FINAL, CORRECTED DOCKERFILE TEMPLATE ---
    _FLASK_DOCKERFILE_TEMPLATE = """
# Stage 1: Build the application dependencies
FROM python:3.10-slim as builder

WORKDIR /app

COPY requirements.txt .
# This command succeeds even if requirements.txt is empty, creating an empty wheels dir
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Create the final production image
FROM python:3.10-slim

WORKDIR /app

# Copy built wheels from the builder stage
COPY --from=builder /app/wheels /wheels

# THE FIX: Install dependencies only if the wheels directory is not empty.
# This prevents 'pip install' from failing on an empty directory when no requirements exist.
RUN if [ -n "$(ls -A /wheels)" ]; then pip install --no-cache /wheels/*; fi

# Copy application code
COPY . .

# Expose the port Gunicorn will run on
EXPOSE 8080

# Run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "{entrypoint}"]
"""

    def generate_dockerfile(self, repo_path: str, analysis_result: dict) -> str:
        """
        Generates a Dockerfile in the repository root based on the analysis.
        """
        framework = analysis_result.get('framework')
        log.info(f"Starting Dockerfile generation for framework: {framework}")

        if framework == 'flask':
            entrypoint = analysis_result.get('entrypoint_file', 'app:app')
            dockerfile_content = self._FLASK_DOCKERFILE_TEMPLATE.format(entrypoint=entrypoint)
            dockerfile_path = os.path.join(repo_path, 'Dockerfile')
            
            try:
                with open(dockerfile_path, 'w') as f:
                    f.write(dockerfile_content.strip())
                log.info(f"Successfully generated Dockerfile at: {dockerfile_path}")
                return dockerfile_path
            except IOError as e:
                raise exceptions.ContainerizationError(f"Failed to write Dockerfile: {e}")
        else:
            raise exceptions.ContainerizationError(f"Framework '{framework}' is not supported for containerization.")


class DockerManager:
    """
    Manages Docker operations: ECR authentication, image building, and pushing.
    """
    def __init__(self, aws_region: str = 'us-east-1'):
        try:
            self.docker_client = docker.from_env()
            self.ecr_client = boto3.client('ecr', region_name=aws_region)
            log.info("Docker and ECR clients initialized successfully.")
        except docker.errors.DockerException as e:
            raise exceptions.DockerError(
                "Docker daemon is not running or accessible. Please start Docker Desktop."
            ) from e

    def _get_ecr_auth_token(self) -> tuple[str, str, str]:
        """
        Retrieves an authorization token from AWS ECR.
        """
        log.info("Requesting ECR authorization token from AWS...")
        try:
            response = self.ecr_client.get_authorization_token()
            auth_data = response['authorizationData'][0]
            token = base64.b64decode(auth_data['authorizationToken']).decode('utf-8')
            username, password = token.split(':')
            registry = auth_data['proxyEndpoint']
            log.info("Successfully retrieved ECR authorization token.")
            return username, password, registry
        except (ClientError, IndexError) as e:
            raise exceptions.ECRAuthError("Failed to get ECR authorization token from AWS.") from e

    def login_to_ecr(self) -> str:
        """
        Logs the Docker client into the AWS ECR registry.
        Returns the ECR registry URL.
        """
        try:
            username, password, registry = self._get_ecr_auth_token()
            log.info(f"Logging into ECR registry: {registry}")
            self.docker_client.login(username=username, password=password, registry=registry)
            log.info("ECR login successful.")
            return registry
        except exceptions.ECRAuthError:
            raise
        except docker.errors.APIError as e:
            raise exceptions.ECRAuthError(f"Docker API error during ECR login: {e}") from e

    def build_image(self, repo_path: str, image_tag: str):
        """
        Builds a Docker image from a given path and tags it.
        Streams build logs in real-time.
        """
        log.info(f"Building Docker image with tag: {image_tag}")
        try:
            image, build_log_stream = self.docker_client.images.build(
                path=repo_path,
                tag=image_tag,
                rm=True, # Remove intermediate containers after a successful build
                platform="linux/amd64"
            )
            
            for chunk in build_log_stream:
                if 'stream' in chunk:
                    for line in chunk['stream'].splitlines():
                        log.info(f"[BUILD] {line}")
                if 'error' in chunk:
                    raise exceptions.DockerBuildError(f"Error during build: {chunk['error']}")

            log.info(f"Successfully built image: {image.short_id}")
            return image
        except docker.errors.BuildError as e:
            # The streaming log should show the error, but we raise a clean exception
            log.error(f"Docker build failed. See logs above for details from the Docker daemon.")
            raise exceptions.DockerBuildError(f"Docker build failed: {e}") from e
        except docker.errors.APIError as e:
            raise exceptions.DockerError(f"Docker API error during build: {e}") from e

    def push_image(self, image_tag: str):
        """
        Pushes a tagged Docker image to its repository.
        Streams push logs in real-time.
        """
        log.info(f"Pushing image to repository: {image_tag}")
        try:
            push_log_stream = self.docker_client.images.push(image_tag, stream=True, decode=True)
            
            for chunk in push_log_stream:
                if 'status' in chunk:
                    status = chunk['status']
                    progress = chunk.get('progress', '')
                    log.info(f"[PUSH] {status} {progress}")
                    if 'error' in chunk:
                        raise exceptions.DockerPushError(f"Error during push: {chunk['errorDetail']['message']}")
                else:
                    log.info(f"[PUSH] {chunk}")

            log.info("Successfully pushed image.")
        except docker.errors.APIError as e:
            raise exceptions.DockerPushError(f"Docker API error during push: {e}") from e