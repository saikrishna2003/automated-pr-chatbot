"""
Handles Git operations: branch creation, commit, push, and PR creation.
"""

import os
from git import Repo
import requests


def create_branch_and_commit(
    repo_path: str,
    branch_name: str,
    yaml_file_path: str,
    yaml_content: str
):
    repo = Repo(repo_path)
    git = repo.git

    # SAFETY CHECK
    if repo.is_dirty(untracked_files=True):
        raise RuntimeError(
            "Local repository has uncommitted changes. "
            "Please commit or stash them before running the bot."
        )

    git.checkout("main")
    git.pull("origin", "main")

    git.checkout("-b", branch_name)

    os.makedirs(os.path.dirname(yaml_file_path), exist_ok=True)
    with open(yaml_file_path, "w") as f:
        f.write(yaml_content)

    repo.index.add([yaml_file_path])
    repo.index.commit(
        f"Add Glue Database config: {os.path.basename(yaml_file_path)}"
    )

    repo.remote("origin").push(branch_name)

    print(f"✅ Branch '{branch_name}' pushed with YAML only.")


def create_pull_request(
    github_token: str,
    repo_name: str,
    branch_name: str,
    base_branch: str,
    pr_title: str
):
    url = f"https://api.github.com/repos/{repo_name}/pulls"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": pr_title,
        "head": branch_name,
        "base": base_branch,
        "body": "Automated Glue Database intake configuration."
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 201:
        raise RuntimeError(
            f"PR creation failed: {response.status_code} {response.text}"
        )

    return response.json()
