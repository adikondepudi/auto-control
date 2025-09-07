import typer
from core.orchestrator import Orchestrator
from utils.logger import log
from utils.exceptions import AutoDeployerException

app = typer.Typer()

@app.command()
def deploy(
    repo_url: str = typer.Option(..., "--repo-url", help="The GitHub repository URL to deploy."),
    prompt: str = typer.Option(..., "--prompt", help="The natural language prompt describing the deployment target."),
    ecr_repo_name: str = typer.Option(..., "--ecr-repo-name", help="The name of the AWS ECR repository to push the image to."),
    aws_region: str = typer.Option("us-east-2", "--aws-region", help="The AWS region to deploy the infrastructure in.")
):
    """
    Analyzes, builds, pushes, and deploys a code repository to AWS App Runner.
    """
    log.info("Autodeployment Chat System initialized.")
    
    prompt_lower = prompt.lower()
    if 'flask' not in prompt_lower or 'aws' not in prompt_lower:
        log.error("Deployment target not supported.")
        print("Error: This tool currently only supports deploying Flask applications to AWS.")
        raise typer.Exit(code=1)
        
    try:
        orchestrator = Orchestrator()
        orchestrator.run_deployment(repo_url, prompt, ecr_repo_name, aws_region)
    except AutoDeployerException as e:
        log.error(f"A critical error occurred during deployment: {e}")
        print(f"\nDeployment Failed: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred: {e}")
        raise typer.Exit(code=1)

@app.command()
def destroy(
    repo_url: str = typer.Option(..., "--repo-url", help="The GitHub repository URL that was deployed."),
    ecr_repo_name: str = typer.Option(..., "--ecr-repo-name", help="The name of the AWS ECR repository used for the deployment."),
    aws_region: str = typer.Option("us-east-2", "--aws-region", help="The AWS region where the infrastructure was deployed.")
):
    """
    Destroys the AWS infrastructure associated with a repository.
    """
    log.info("Autodeployment Chat System - Destroy initialized.")
    
    try:
        orchestrator = Orchestrator()
        orchestrator.run_destroy(repo_url, ecr_repo_name, aws_region)
    except AutoDeployerException as e:
        log.error(f"A critical error occurred during destroy: {e}")
        print(f"\nDestroy Failed: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()