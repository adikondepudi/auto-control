import os
import tempfile
import git
from utils import exceptions
from utils.logger import log

class RepoAnalyzer:
    """
    Analyzes a Git repository to identify the framework and language.
    """
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.temp_dir = tempfile.TemporaryDirectory()

    def analyze(self) -> dict:
        """
        Clones a repository and analyzes its content to detect the framework.

        Returns:
            dict: A dictionary containing analysis results.
        Raises:
            RepoAnalysisError: If cloning fails or framework is not supported.
        """
        log.info(f"Starting analysis for repository: {self.repo_url}")
        try:
            # Clones the specific branch, useful for repos where main isn't the default
            git.Repo.clone_from(self.repo_url, self.temp_dir.name)
            log.info(f"Successfully cloned repository into {self.temp_dir.name}")
            
            analysis_result = self._detect_framework(self.temp_dir.name)
            log.info(f"Analysis complete. Detected framework: {analysis_result['framework']}")
            return analysis_result
        except git.GitCommandError as e:
            raise exceptions.RepoAnalysisError(f"Failed to clone repository: {e}")
        finally:
            log.info(f"Cleaning up temporary directory: {self.temp_dir.name}")
            self.temp_dir.cleanup()


    def _detect_framework(self, path: str) -> dict:
        """
        Private helper to detect the specific framework used in the code.
        This version prioritizes code analysis over file existence.

        Args:
            path (str): The local path to the cloned repository.

        Returns:
            dict: A dictionary with framework details.
        Raises:
            RepoAnalysisError: If no supported framework is found.
        """
        # Iterate through all files to find a potential Flask app
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            # The most reliable check for a Flask app
                            if "from flask import Flask" in f.read():
                                log.info(f"Found Flask import in '{file}'. Identifying as Flask project.")
                                
                                # Check for requirements.txt as a good practice, but don't fail if it's missing
                                if not os.path.exists(os.path.join(path, 'requirements.txt')):
                                    log.warning("No 'requirements.txt' file found. Deployment might fail if dependencies are needed.")

                                # Assumption for MVP: entrypoint is 'app' object in the detected file
                                entrypoint_module = os.path.splitext(file)[0]
                                return {
                                    'framework': 'flask',
                                    'language': 'python',
                                    'entrypoint_file': f"{entrypoint_module}:app",
                                    'local_path': path
                                }
                    except Exception as e:
                        log.warning(f"Could not read or process file {file}: {e}")
        
        # If the loop completes without finding a Flask import
        raise exceptions.RepoAnalysisError("Could not detect a supported framework (only Flask is supported).")