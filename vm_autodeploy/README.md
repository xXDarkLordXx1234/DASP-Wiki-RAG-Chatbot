
# VM Auto Deploy

This autodeploy script is designed to run on a VM and automatically deploy the latest version of the RAG retriever service by fetching the latest GitLab release from the main branch.

## Setup

1. Clone the repository to the VM
2. Create a new python 3.11 virtual environment
3. Install the requirements
4. Define the environment variables
    ```env
    PROJECT_DIR=/path/the/repo
    GITLAB_USERNAME=your_gitlab_username
    GITLAB_TOKEN=your_gitlab_token
    GITLAB_REPO=your_gitlab_repo

    # The path to the wiki data
    SOURCE_DATA_PATH=/path/to/your/data

    # Where to store the index
    INDEX_DATA_PATH=/path/to/your/index
    ```
5. Now either run the script manually or create a systemd service to run the script automatically
6. Calling `curl -X POST "http://<vm_ip>:5000/deploy/"` will trigger the deployment
