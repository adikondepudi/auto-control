# FILE: core/analyzer.py

import os
import re # Import the regular expression module
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

    def _patch_hardcoded_urls(self, repo_path: str):
        """
        Scans frontend files for hardcoded localhost URLs and replaces them
        with relative paths to ensure portability after deployment.
        """
        log.info("Scanning for hardcoded localhost URLs to patch...")
        # Regex to find http://localhost or http://127.0.0.1 with an optional port
        url_pattern = re.compile(r"https?://(localhost|127\.0\.0\.1)(:\d+)?")
        
        patched_files_count = 0
        for root, _, files in os.walk(repo_path):
            if '.git' in root:
                continue
            
            for file_name in files:
                if file_name.endswith(('.js', '.html', '.htm')):
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r+', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Replace matched URLs with an empty string, making the path relative
                            new_content, substitutions_made = url_pattern.subn('', content)
                            
                            if substitutions_made > 0:
                                log.info(f"Patched {substitutions_made} hardcoded URL(s) in '{os.path.relpath(file_path, repo_path)}'.")
                                # Rewrite the file with the patched content
                                f.seek(0)
                                f.truncate()
                                f.write(new_content)
                                patched_files_count += 1
                    except Exception as e:
                        log.warning(f"Could not read or patch file {file_path}: {e}")
        
        if patched_files_count > 0:
            log.info(f"URL patching complete. Total files patched: {patched_files_count}.")
        else:
            log.info("No hardcoded localhost URLs found to patch.")

    def _detect_framework(self, path: str) -> dict:
        """
        Private helper to detect the framework, handle dependencies, and patch code.
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
                                
                                # --- ROBUST requirements.txt DISCOVERY & CONSOLIDATION ---
                                found_requirements_path = None
                                for r_root, _, r_files in os.walk(path):
                                    if '.git' in r_root: continue
                                    if 'requirements.txt' in r_files:
                                        found_requirements_path = os.path.join(r_root, 'requirements.txt')
                                        log.info(f"Discovered 'requirements.txt' at: {os.path.relpath(found_requirements_path, path)}")
                                        break
                                
                                root_requirements_path = os.path.join(path, 'requirements.txt')

                                if found_requirements_path:
                                    if found_requirements_path != root_requirements_path:
                                        log.info(f"Consolidating '{os.path.relpath(found_requirements_path, path)}' to the repository root.")
                                        with open(found_requirements_path, 'r') as source, open(root_requirements_path, 'w') as dest:
                                            dest.write(source.read())
                                else:
                                    log.warning("No 'requirements.txt' file found. A new one will be created.")
                                    open(root_requirements_path, 'w').close()

                                with open(root_requirements_path, 'r+') as req_file:
                                    content = req_file.read().lower()
                                    deps_to_add = []
                                    if 'flask' not in content: deps_to_add.append('Flask')
                                    if 'gunicorn' not in content: deps_to_add.append('gunicorn')
                                    if deps_to_add:
                                        log.info(f"Injecting missing core dependencies: {', '.join(deps_to_add)}")
                                        req_file.seek(0, os.SEEK_END)
                                        if req_file.tell() > 0: req_file.write('\n')
                                        req_file.write('\n'.join(deps_to_add))
                                
                                # --- INTELLIGENT ENTRYPOINT DETECTION ---
                                module_name = os.path.splitext(file)[0]
                                relative_dir = os.path.relpath(root, path)
                                full_module_path = module_name if relative_dir == '.' else f"{relative_dir.replace(os.sep, '.')}.{module_name}"
                                entrypoint = f"{full_module_path}:app"
                                log.info(f"Determined application entrypoint: {entrypoint}")
                                
                                # --- NEW FINAL STEP: Patch hardcoded URLs in frontend files ---
                                self._patch_hardcoded_urls(path)

                                return {
                                    'framework': 'flask',
                                    'language': 'python',
                                    'entrypoint_file': entrypoint,
                                }
                    except Exception as e:
                        log.warning(f"Could not read or process file {file}: {e}")
        
        raise exceptions.RepoAnalysisError("Could not detect a supported framework (only Flask is supported).")