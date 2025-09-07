# Auto-Control: A Zero-DevOps Deployment Engine

Auto-Control is a command-line tool that automates the deployment of web applications from a GitHub repository to the cloud, guided by a simple natural language prompt. It is designed for developers with little to no DevOps experience, abstracting away the complexities of containerization and infrastructure provisioning.

---

## Prerequisites

Before you begin, ensure you have the following installed and configured:
*   Python 3.10+
*   Docker Desktop (must be running)
*   Terraform CLI
*   AWS CLI (with credentials configured via `aws configure` or environment variables)

---

## Setup

1.  **Clone the repository:**
    ```bash
    git clone [Your-GitHub-Repo-URL]
    cd auto-control
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
---

## Usage

The tool has two main commands: `deploy` and `destroy`.

### Deploy an Application

This command will analyze, containerize, and deploy a Flask application to AWS App Runner.

```bash
python main.cli.py deploy \
  --repo-url "https://github.com/Arvo-AI/hello_world" \
  --prompt "Deploy my flask app to AWS" \
  --ecr-repo-name "hello-world-arvo-test" \
  --aws-region "us-east-1"
  --ecr-repo-name: Important: This ECR repository must be created in your AWS account before running the command.
```

### Destroy Infrastructure

This command will tear down all AWS resources created by a specific deployment.

```bash
python main.cli.py destroy \
  --repo-url "https://github.com/Arvo-AI/hello_world" \
  --ecr-repo-name "hello-world-arvo-test" \
  --aws-region "us-east-1"
```

### Destroy Infrastructure
*   Typer (for the CLI)
*   GitPython (for cloning repositories)
*   Boto3 (AWS SDK)
*   Docker SDK for Python
*   All other dependencies are part of the standard Python library.
