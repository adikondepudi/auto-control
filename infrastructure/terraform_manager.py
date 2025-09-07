import subprocess
import os
import json
from utils import exceptions
from utils.logger import log

class TerraformManager:
    """
    A Python wrapper for executing Terraform commands.
    """
    def __init__(self, working_dir: str):
        self.working_dir = working_dir
        if not os.path.exists(self.working_dir):
            raise exceptions.TerraformError(f"Terraform working directory does not exist: {self.working_dir}")

    def _run_command(self, command: list) -> str:
        """
        Executes a shell command and streams its output.

        Args:
            command (list): The command to execute as a list of strings.

        Returns:
            str: The captured stdout from the command.
        Raises:
            TerraformError: If the command returns a non-zero exit code.
        """
        log.info(f"Executing Terraform command: {' '.join(command)}")
        try:
            process = subprocess.Popen(
                command,
                cwd=self.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            
            stdout_lines = []
            for line in iter(process.stdout.readline, ''):
                log.info(line.strip())
                stdout_lines.append(line)
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, command)

            return "".join(stdout_lines)

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error(f"Terraform command failed: {e}")
            raise exceptions.TerraformError(f"An error occurred while running Terraform: {e}")

    def init(self):
        """Runs 'terraform init'."""
        self._run_command(['terraform', 'init'])

    def apply(self, variables: dict) -> dict:
        """
        Runs 'terraform apply' with variables.

        Args:
            variables (dict): A dictionary of Terraform variables.

        Returns:
            dict: The Terraform output variables.
        """
        command = ['terraform', 'apply', '-auto-approve', '-json']
        for key, value in variables.items():
            command.append(f'-var={key}={value}')
        
        self._run_command(command)
        return self.get_outputs()


    def destroy(self, variables: dict):
        """Runs 'terraform destroy'."""
        command = ['terraform', 'destroy', '-auto-approve']
        for key, value in variables.items():
            command.append(f'-var={key}={value}')

        self._run_command(command)
        log.info("Terraform destroy completed successfully.")
        
    def get_outputs(self) -> dict:
        """
        Runs 'terraform output -json' and returns the parsed JSON.

        Returns:
            dict: The parsed output variables from Terraform.
        """
        output_json = self._run_command(['terraform', 'output', '-json'])
        try:
            outputs = json.loads(output_json)
            # The output values have a 'value' key, let's simplify that
            return {key: val['value'] for key, val in outputs.items()}
        except json.JSONDecodeError:
            raise exceptions.TerraformError("Failed to parse Terraform output JSON.")