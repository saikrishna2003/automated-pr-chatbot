"""
Git Operations Service
Enhanced with better PR conflict detection and handling
"""

import os
from typing import Dict, Any
from git import Repo
import requests


def create_pull_request(
    github_token: str,
    repo_name: str,
    pr_title: str,
    pr_body: str = None
) -> Dict[str, Any]:
    """
    Create PR from fork dev -> upstream dev
    Enhanced with better error messages for PR conflicts
    """

    fork_owner = os.getenv("GITHUB_USERNAME")
    if not fork_owner:
        raise RuntimeError(
            "GITHUB_USERNAME not set in environment. "
            "Please add your GitHub username to .env file."
        )

    url = f"https://api.github.com/repos/{repo_name}/pulls"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if pr_body is None:
        pr_body = (
            "## Automated Data Platform Intake\n\n"
            "This PR was generated automatically by the Data Platform Intake Bot.\n\n"
            "- Source: fork `dev` branch\n"
            "- Target: upstream `dev` branch\n"
        )

    # The head should be in format: "username:branch"
    payload = {
        "title": pr_title,
        "head": f"{fork_owner}:dev",
        "base": "dev",
        "body": pr_body,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 201:
            return response.json()

        # Handle specific error cases
        error_data = response.json()

        if response.status_code == 422:
            # Check if it's a duplicate PR error
            if "pull request already exists" in str(error_data).lower():
                # Try to get the existing PR URL
                existing_pr_url = get_existing_pr_url(github_token, repo_name, fork_owner)

                raise RuntimeError(
                    f"A pull request already exists from {fork_owner}:dev to {repo_name}:dev.\n"
                    f"Existing PR: {existing_pr_url if existing_pr_url else 'Check your PRs on GitHub'}\n\n"
                    "Options:\n"
                    "1. Close the existing PR and create a new one\n"
                    "2. Your changes have been pushed to your fork's dev branch and will appear in the existing PR"
                )
            else:
                raise RuntimeError(f"GitHub API validation error: {error_data}")

        elif response.status_code == 401:
            raise RuntimeError(
                "Authentication failed. Please check your GITHUB_TOKEN in .env file."
            )

        elif response.status_code == 404:
            raise RuntimeError(
                f"Repository '{repo_name}' not found or you don't have access. "
                "Please verify REPO_NAME in .env file."
            )

        else:
            raise RuntimeError(
                f"GitHub API error (status {response.status_code}): {response.text}"
            )

    except requests.exceptions.Timeout:
        raise RuntimeError("GitHub API request timed out. Please try again.")

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Failed to connect to GitHub API. "
            "Please check your internet connection."
        )

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"GitHub API request failed: {str(e)}")


def get_existing_pr_url(github_token: str, repo_name: str, fork_owner: str) -> str:
    """
    Get URL of existing PR from fork to upstream
    """
    try:
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        params = {
            "state": "open",
            "head": f"{fork_owner}:dev",
            "base": "dev"
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            prs = response.json()
            if prs and len(prs) > 0:
                return prs[0]["html_url"]

        return None

    except Exception:
        return None


def check_existing_pr(github_token: str, repo_name: str, fork_owner: str) -> Dict[str, Any]:
    """
    Check if there's an existing open PR from fork dev to upstream dev

    Returns:
        Dictionary with 'exists' (bool) and 'url' (str if exists)
    """
    try:
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        params = {
            "state": "open",
            "head": f"{fork_owner}:dev",
            "base": "dev"
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            prs = response.json()
            if prs and len(prs) > 0:
                return {
                    "exists": True,
                    "url": prs[0]["html_url"],
                    "title": prs[0]["title"],
                    "number": prs[0]["number"]
                }

        return {"exists": False}

    except Exception as e:
        print(f"Error checking existing PR: {e}")
        return {"exists": False}