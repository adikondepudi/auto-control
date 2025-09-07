import subprocess
import os
import json
from utils import exceptions
from utils.logger import log

class TerraformManager:
    """
    A Python wrapper for executing Terraform commands with detailed error reporting.
    """
    def __init__(self, working_dir: str):
        self.working_dir = working_dir
        if not os.path.exists(self.working_dir):
            raise exceptions.TerraformError(f"Terraform working directory does not exist: {self.working_dir}")

    def _run_command(self, command: list) -> str:
        """
        Executes a shell command, streams its output, and parses errors.
        """
        log.info(f"Executing Terraform command: {' '.join(command)}")
        full_output = []
        try:
            process = subprocess.Popen(
                command,
                cwd=self.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            
            for line in iter(process.stdout.readline, ''):
                log.info(line.strip())
                full_output.append(line)
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code != 0:
                # --- NEW: More detailed error parsing ---
                # Join the full output and try to find the specific error summary.
                output_str = "".join(full_output)
                error_summary = self._parse_terraform_error(output_str)
                
                # Raise an exception with the detailed error message.
                raise subprocess.CalledProcessError(return_code, command, output=error_summary)

            return "".join(full_output)

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # If our parsing worked, e.output will have the specific error.
            detailed_error = e.output if hasattr(e, 'output') and e.output else str(e)
            log.error(f"Terraform command failed: {detailed_error}")
            raise exceptions.TerraformError(f"Terraform command failed: {detailed_error}")

    def _parse_terraform_error(self, output: str) -> str:
        """
        Parses the line-by-line JSON output from Terraform to find the error summary.
        """
        # Terraform's JSON output streams one object per line.
        for line in output.splitlines():
            try:
                line_json = json.loads(line)
                # This is the structure Terraform uses for error diagnostics.
                if line_json.get("@level") == "error" and "diagnostic" in line_json:
                    summary = line_json["diagnostic"].get("summary", "No summary found.")
                    detail = line_json["diagnostic"].get("detail", "No details found.")
                    return f"{summary} | Detail: {detail}"
            except json.JSONDecodeError:
                # Ignore lines that are not valid JSON.
                continue
        return "Could not parse specific error from Terraform output."

    def init(self):
        """Runs 'terraform init'."""
        self._run_command(['terraform', 'init', '-no-color'])

    def apply(self, variables: dict) -> dict:
        """
        Runs 'terraform apply' with variables.
        """
        command = ['terraform', 'apply', '-auto-approve', '-json']
        for key, value in variables.items():
            command.append(f'-var={key}={value}')
        
        self._run_command(command)
        return self.get_outputs()

    def destroy(self, variables: dict):
        """Runs 'terraform destroy'."""
        command = ['terraform', 'destroy', '-auto-approve', '-json']
        for key, value in variables.items():
            command.append(f'-var={key}={value}')
        self._run_command(command)
        log.info("Terraform destroy completed successfully.")
        
    def get_outputs(self) -> dict:
        """
        Runs 'terraform output -json' and returns the parsed JSON.
        """
        try:
            output_json = self._run_command(['terraform', 'output', '-json'])
            outputs = json.loads(output_json)
            return {key: val['value'] for key, val in outputs.items()}
        except (json.JSONDecodeError, exceptions.TerraformError):
            # If apply failed, there are no outputs. Return empty dict.
            log.warning("Could not retrieve Terraform outputs. This is expected if the apply failed.")
            return {}