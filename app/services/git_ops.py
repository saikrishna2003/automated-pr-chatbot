"""
Git Operations Service
Handles Git repository operations and GitHub PR creation
"""

import os
from typing import Dict, Any
from git import Repo
import requests


def commit_yaml_to_dev(
    repo_path: str,
    yaml_file_path: str,
    yaml_content: str
) -> None:
    """
    Commit YAML file directly to fork's dev branch
    """
    try:
        repo = Repo(repo_path)
        git = repo.git

        # Ensure clean working tree
        if repo.is_dirty(untracked_files=True):
            raise RuntimeError(
                "Repository has uncommitted changes. "
                "Please commit or stash them before running the bot."
            )

        # Checkout and update dev
        git.checkout("dev")
        git.pull("origin", "dev")

        # Ensure directory exists
        os.makedirs(os.path.dirname(yaml_file_path), exist_ok=True)

        # Write YAML file
        with open(yaml_file_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        # Commit
        repo.index.add([yaml_file_path])
        repo.index.commit(
            f"Add Glue DB config: {os.path.basename(yaml_file_path)}"
        )

        # Push to fork dev
        repo.remote("origin").push("dev")

    except Exception as e:
        raise Exception(f"Git operation failed: {str(e)}")


def create_pull_request(
    github_token: str,
    repo_name: str,
    pr_title: str,
    pr_body: str = None
) -> Dict[str, Any]:
    """
    Create PR from fork dev -> upstream dev
    """

    fork_owner = os.getenv("GITHUB_USERNAME")
    if not fork_owner:
        raise RuntimeError("GITHUB_USERNAME not set in environment")

    url = f"https://api.github.com/repos/{repo_name}/pulls"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if pr_body is None:
        pr_body = (
            "## Automated Glue Database Intake\n\n"
            "This PR was generated automatically by the Data Platform Intake Bot.\n\n"
            "- Source: fork `dev`\n"
            "- Target: upstream `dev`\n"
        )

    payload = {
        "title": pr_title,
        "head": "downloadmail8883-cyber:dev",
        "base": "dev",
        "body": pr_body,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 201:
        return response.json()

    raise RuntimeError(
        f"GitHub API error ({response.status_code}): {response.text}"
    )
