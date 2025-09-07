import os
import boto3
from botocore.exceptions import ClientError
from core.analyzer import RepoAnalyzer
from core.containerizer import Containerizer, DockerManager
from infrastructure.terraform_manager import TerraformManager
from utils.logger import log
from utils import exceptions

class Orchestrator:
    """
    Coordinates the entire deployment workflow from analysis to provisioning.
    """

    def _get_aws_account_id(self):
        """Retrieves the AWS Account ID from the current session."""
        try:
            sts_client = boto3.client("sts")
            return sts_client.get_caller_identity()["Account"]
        except ClientError as e:
            raise exceptions.AutoDeployerException(f"Could not determine AWS Account ID: {e}")

    def run_deployment(self, repo_url: str, prompt: str, ecr_repo_name: str, aws_region: str):
        """
        Executes the full, end-to-end deployment pipeline.
        """
        log.info("=" * 50)
        log.info(f"Starting new deployment for {repo_url}")
        log.info(f"ECR Repository: {ecr_repo_name}")
        log.info("=" * 50)

        aws_account_id = self._get_aws_account_id()
        log.info(f"Operating in AWS Account '{aws_account_id}' and Region '{aws_region}'")

        # Context manager handles cloning and cleanup
        with RepoAnalyzer(repo_url) as analysis_result:
            local_repo_path = analysis_result['local_path']
            commit_hash = analysis_result['commit_hash']

            log.info("[STEP 1/4] Generating Dockerfile...")
            containerizer = Containerizer()
            containerizer.generate_dockerfile(local_repo_path, analysis_result)

            log.info("[STEP 2/4] Building and pushing container image...")
            docker_manager = DockerManager(aws_region=aws_region)
            
            registry_url = docker_manager.login_to_ecr()
            clean_registry_url = registry_url.replace("https://", "")
            
            image_tag = f"{clean_registry_url}/{ecr_repo_name}:{commit_hash}"
            
            docker_manager.build_image(local_repo_path, image_tag)
            docker_manager.push_image(image_tag)
            log.info(f"Successfully pushed image: {image_tag}")

            log.info("[STEP 3/4] Provisioning infrastructure with Terraform...")
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            service_name = f"auto-deployed-{repo_name}"

            terraform_template_path = os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'templates', 'aws_app_runner')
            tf_manager = TerraformManager(working_dir=terraform_template_path)
            
            tf_vars = {
                "service_name": service_name,
                "image_identifier": image_tag,
                "aws_account_id": aws_account_id,
                "aws_region": aws_region,
                "ecr_repo_name": ecr_repo_name
            }
            
            log.info("Initializing Terraform...")
            tf_manager.init()
            log.info("Applying Terraform configuration...")
            outputs = tf_manager.apply(variables=tf_vars)
            
            log.info("[STEP 4/4] Finalizing deployment...")
            service_url = outputs.get('service_url')
            if service_url:
                log.info("=" * 50)
                log.info("🚀 DEPLOYMENT SUCCESSFUL! 🚀")
                log.info(f"Service URL: {service_url}")
                log.info("=" * 50)
            else:
                log.error("Deployment finished, but service URL was not found in Terraform output.")
    
    def run_destroy(self, repo_url: str, ecr_repo_name: str, aws_region: str):
        """Executes the full infrastructure teardown."""
        log.info("=" * 50)
        log.info(f"Starting teardown for {repo_url} in region {aws_region}")
        log.info("=" * 50)

        aws_account_id = self._get_aws_account_id()
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        service_name = f"auto-deployed-{repo_name}"
        log.info(f"Identified service name to destroy: {service_name}")
        
        dummy_image_tag = f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{ecr_repo_name}:latest"

        terraform_template_path = os.path.join(os.path.dirname(__file__), '..', 'infrastructure', 'templates', 'aws_app_runner')
        tf_manager = TerraformManager(working_dir=terraform_template_path)
        
        tf_vars = {
            "service_name": service_name,
            "image_identifier": dummy_image_tag,
            "aws_account_id": aws_account_id,
            "aws_region": aws_region,
            "ecr_repo_name": ecr_repo_name
        }
        
        log.info("Initializing Terraform...")
        tf_manager.init()
        log.info("Destroying Terraform-managed infrastructure...")
        tf_manager.destroy(variables=tf_vars)

        log.info("=" * 50)
        log.info("🚀 DESTROY SUCCESSFUL! 🚀")
        log.info("=" * 50)