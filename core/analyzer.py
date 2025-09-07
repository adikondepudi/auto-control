# FILE: core/analyzer.py

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
            if '.git' in root:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            if "from flask import Flask" in f.read():
                                log.info(f"Found Flask import in '{file}'. Identifying as Flask project.")
                                
                                # --- THE FIX: ROBUST requirements.txt DISCOVERY & CONSOLIDATION ---
                                found_requirements_path = None
                                # Search the entire repo for a requirements.txt file
                                for r_root, _, r_files in os.walk(path):
                                    if '.git' in r_root:
                                        continue
                                    if 'requirements.txt' in r_files:
                                        found_requirements_path = os.path.join(r_root, 'requirements.txt')
                                        log.info(f"Discovered 'requirements.txt' at: {os.path.relpath(found_requirements_path, path)}")
                                        break # Use the first one we find

                                root_requirements_path = os.path.join(path, 'requirements.txt')

                                if found_requirements_path:
                                    # If a requirements file was found but isn't in the root,
                                    # copy its content to the root to standardize the build process.
                                    if found_requirements_path != root_requirements_path:
                                        log.info(f"Consolidating '{os.path.relpath(found_requirements_path, path)}' to the repository root for containerization.")
                                        with open(found_requirements_path, 'r') as source_file, open(root_requirements_path, 'w') as dest_file:
                                            dest_file.write(source_file.read())
                                else:
                                    log.warning("No 'requirements.txt' file found anywhere in the repository. A new one will be created.")
                                    open(root_requirements_path, 'w').close()

                                # Now, operate *only* on the root_requirements_path. This standardizes the input for the Docker build.
                                with open(root_requirements_path, 'r+') as req_file:
                                    content = req_file.read().lower()
                                    dependencies_to_add = []
                                    if 'flask' not in content:
                                        dependencies_to_add.append('Flask')
                                    if 'gunicorn' not in content:
                                        dependencies_to_add.append('gunicorn')

                                    if dependencies_to_add:
                                        log.info(f"Injecting missing core dependencies into requirements.txt: {', '.join(dependencies_to_add)}")
                                        req_file.seek(0, os.SEEK_END)
                                        if req_file.tell() > 0:
                                            req_file.write('\n')
                                        req_file.write('\n'.join(dependencies_to_add))
                                
                                # --- INTELLIGENT ENTRYPOINT DETECTION (FROM PREVIOUS FIX) ---
                                module_name = os.path.splitext(file)[0]
                                relative_dir = os.path.relpath(root, path)
                                if relative_dir == '.':
                                    full_module_path = module_name
                                else:
                                    python_path = relative_dir.replace(os.sep, '.')
                                    full_module_path = f"{python_path}.{module_name}"
                                
                                entrypoint = f"{full_module_path}:app"
                                log.info(f"Determined application entrypoint: {entrypoint}")

                                return {
                                    'framework': 'flask',
                                    'language': 'python',
                                    'entrypoint_file': entrypoint,
                                }
                    except Exception as e:
                        log.warning(f"Could not read or process file {file}: {e}")
        
        raise exceptions.RepoAnalysisError("Could not detect a supported framework (only Flask is supported).")