import os
import tempfile
import git
from utils import exceptions
from utils.logger import log

class RepoAnalyzer:
    """
    Analyzes a Git repository to identify the framework and language.
    Designed to be used as a context manager to handle temporary directory cleanup.
    """
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = None

    def __enter__(self):
        """Clones the repo and performs analysis upon entering the context."""
        log.info(f"Starting analysis for repository: {self.repo_url}")
        try:
            self.repo = git.Repo.clone_from(self.repo_url, self.temp_dir.name)
            log.info(f"Successfully cloned repository into {self.temp_dir.name}")
            
            analysis_result = self._detect_framework(self.temp_dir.name)
            commit_hash = self.repo.head.object.hexsha[:7]
            analysis_result['commit_hash'] = commit_hash
            analysis_result['local_path'] = self.temp_dir.name
            
            log.info(f"Analysis complete. Detected framework: {analysis_result['framework']} at commit {commit_hash}")
            return analysis_result
        except git.GitCommandError as e:
            raise exceptions.RepoAnalysisError(f"Failed to clone repository: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleans up the temporary directory upon exiting the context."""
        log.info(f"Cleaning up temporary directory: {self.temp_dir.name}")
        self.temp_dir.cleanup()

    def _detect_framework(self, path: str) -> dict:
        """
        Private helper to detect the framework and ensure core dependencies exist.
        """
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            if "from flask import Flask" in f.read():
                                log.info(f"Found Flask import in '{file}'. Identifying as Flask project.")
                                
                                # --- THE WINNING LOGIC IS HERE ---
                                requirements_path = os.path.join(path, 'requirements.txt')
                                if not os.path.exists(requirements_path):
                                    log.warning("No 'requirements.txt' file found. A new one will be created with core dependencies.")
                                    # Create an empty file to be appended to.
                                    open(requirements_path, 'w').close()

                                # Now, read the file and ensure core dependencies are present.
                                with open(requirements_path, 'r+') as req_file:
                                    content = req_file.read().lower()
                                    dependencies_to_add = []
                                    
                                    # Check for Flask
                                    if 'flask' not in content:
                                        dependencies_to_add.append('Flask')
                                    # Check for Gunicorn
                                    if 'gunicorn' not in content:
                                        dependencies_to_add.append('gunicorn')

                                    if dependencies_to_add:
                                        log.info(f"Injecting missing core dependencies into requirements.txt: {', '.join(dependencies_to_add)}")
                                        # Go to the end of the file to append
                                        req_file.seek(0, os.SEEK_END)
                                        # Add a newline if the file is not empty
                                        if req_file.tell() > 0:
                                            req_file.write('\n')
                                        req_file.write('\n'.join(dependencies_to_add))
                                
                                entrypoint_module = os.path.splitext(file)[0]
                                return {
                                    'framework': 'flask',
                                    'language': 'python',
                                    'entrypoint_file': f"{entrypoint_module}:app",
                                }
                    except Exception as e:
                        log.warning(f"Could not read or process file {file}: {e}")
        
        raise exceptions.RepoAnalysisError("Could not detect a supported framework (only Flask is supported).")