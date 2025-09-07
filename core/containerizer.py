import os
from utils import exceptions
from utils.logger import log

class Containerizer:
    """
    Handles the generation of containerization files, like Dockerfiles.
    """
    
    _FLASK_DOCKERFILE_TEMPLATE = """
# Stage 1: Build the application
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Create the final production image
FROM python:3.10-slim

WORKDIR /app

# Copy built wheels from the builder stage
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache /wheels/*

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

        Args:
            repo_path (str): The local path to the cloned repository.
            analysis_result (dict): The result from the RepoAnalyzer.

        Returns:
            str: The path to the generated Dockerfile.
        Raises:
            ContainerizationError: If the framework is not supported.
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