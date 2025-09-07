import os
import re
from core.analyzer import RepoAnalyzer
from infrastructure.terraform_manager import TerraformManager
from utils.logger import log

class Orchestrator:
    """
    Coordinates the entire deployment workflow from analysis to provisioning.
    """

    def run_deployment(self, repo_url: str, prompt: str):
        """
        Executes the full deployment pipeline.

        Args:
            repo_url (str): The URL of the GitHub repository to deploy.
            prompt (str): The natural language prompt describing the deployment.
        """
        log.info("=" * 50)
        log.info(f"Starting new deployment for {repo_url}")
        log.info(f"Prompt: '{prompt}'")
        log.info("=" * 50)

        # 1. Analyze Repository
        log.info("[STEP 1/3] Analyzing repository...")
        analyzer = RepoAnalyzer(repo_url)
        analysis_result = analyzer.analyze()
        log.info(f"Analysis successful: {analysis_result}")

        # 2. Containerize (Simulated)
        log.info("[STEP 2/3] Containerizing application...")
        log.warning("SKIPPING: Docker build and push to ECR. Using a public placeholder image for deployment.")
        placeholder_image = "public.ecr.aws/aws-containers/hello-app-runner:latest"
        log.info(f"Using placeholder image: {placeholder_image}")

        # 3. Provision Infrastructure
        log.info("[STEP 3/3] Provisioning infrastructure with Terraform...")
        
        # Derive a service name from the repo URL
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        service_name = f"auto-deployed-{repo_name}"
        log.info(f"Generated service name: {service_name}")

        # The Terraform templates are in a fixed location relative to this script
        terraform_template_path = os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'templates', 'aws_app_runner')
        
        tf_manager = TerraformManager(working_dir=terraform_template_path)
        
        tf_vars = {
            "service_name": service_name,
            "image_identifier": placeholder_image
        }
        
        log.info("Initializing Terraform...")
        tf_manager.init()
        
        log.info("Applying Terraform configuration...")
        outputs = tf_manager.apply(variables=tf_vars)
        
        service_url = outputs.get('service_url')
        if service_url:
            log.info("=" * 50)
            log.info("🚀 DEPLOYMENT SUCCESSFUL! 🚀")
            log.info(f"Service URL: {service_url}")
            log.info("=" * 50)
        else:
            log.error("Deployment finished, but service URL was not found in Terraform output.")

    def run_destroy(self, repo_url: str):
        """
        Executes the full infrastructure teardown.

        Args:
            repo_url (str): The URL of the GitHub repository that was deployed.
        """
        log.info("=" * 50)
        log.info(f"Starting teardown for {repo_url}")
        log.info("=" * 50)

        # Derive the service name from the repo URL, just like in deployment
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        service_name = f"auto-deployed-{repo_name}"
        log.info(f"Identified service name to destroy: {service_name}")

        # The image identifier is also needed for Terraform to validate the plan,
        # even during destroy.
        placeholder_image = "public.ecr.aws/aws-containers/hello-app-runner:latest"

        terraform_template_path = os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'templates', 'aws_app_runner')
        
        tf_manager = TerraformManager(working_dir=terraform_template_path)
        
        tf_vars = {
            "service_name": service_name,
            "image_identifier": placeholder_image
        }
        
        log.info("Initializing Terraform...")
        tf_manager.init()

        log.info("Destroying Terraform-managed infrastructure...")
        tf_manager.destroy(variables=tf_vars)

        log.info("=" * 50)
        log.info("🚀 DESTROY SUCCESSFUL! 🚀")
        log.info("=" * 50)