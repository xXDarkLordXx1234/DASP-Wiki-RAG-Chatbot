import logging
import os
import shutil
import subprocess
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("autodeploy.log")
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

app = FastAPI()


def update() -> None:
    """
    Deploy the project to the server.
    """
    load_dotenv()
    root_path = Path(__file__).parent.parent.resolve()
    if not os.getenv("PROJECT_DIR"):
        logger.error("PROJECT_DIR environment variable not set")
        raise HTTPException(
            status_code=500, detail="PROJECT_DIR environment variable not set"
        )
    if not os.getenv("GITLAB_USERNAME"):
        logger.error("GITLAB_USERNAME environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="GITLAB_USERNAME environment variable not set",
        )
    if not os.getenv("GITLAB_TOKEN"):
        logger.error("GITLAB_TOKEN environment variable not set")
        raise HTTPException(
            status_code=500, detail="GITLAB_TOKEN environment variable not set"
        )
    if not os.getenv("GITLAB_REPO"):
        logger.error("GITLAB_REPO environment variable not set")
        raise HTTPException(
            status_code=500, detail="GITLAB_REPO environment variable not set"
        )

    project_path = root_path / os.environ["PROJECT_DIR"]

    repo_url = "https://{username}:{token}@{repo}.git".format(
        token=os.environ["GITLAB_TOKEN"],
        username=os.environ["GITLAB_USERNAME"],
        repo=os.environ["GITLAB_REPO"],
    )

    try:
        os.chdir(str(project_path))
        subprocess.run(
            [
                "git",
                "remote",
                "set-url",
                "origin",
                repo_url,
            ],
            check=True,
        )
        subprocess.run(["git", "pull", "origin", "main"], check=True)

        env_file = Path(__file__).parent.resolve() / ".env"
        env_project = project_path / ".env"
        if env_project.exists():
            env_project.unlink()
        shutil.copy(env_file, env_project)

        subprocess.run(["sudo", "docker-compose", "down"], check=True)
        subprocess.run(["sudo", "docker", "image", "prune", "-f"], check=True)
        subprocess.run(
            ["sudo", "docker-compose", "up", "--build", "-d"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Deployment failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        )
    logger.info("Project deployed successfully!")


@app.post("/deploy/")
async def deploy(request: Request) -> dict[str, str]:
    """
    Deploy the project to the server.

    Returns
    -------
    dict[str, str]
        A dictionary containing the status and message of the deployment.
    """
    update()
    return {
        "status": "success",
        "message": "Project deployed successfully!",
    }


if __name__ == "__main__":
    update()
    uvicorn.run(app, host="0.0.0.0", port=5000)
