"""
Glue Database PR Tool
Creates YAML, commits to fork dev, raises PR to upstream dev
"""

import os
import traceback
from pydantic import BaseModel, Field, validator

from app.services.yaml_generator import generate_yaml
from app.services.git_ops import commit_yaml_to_dev, create_pull_request


class GlueDBPRInput(BaseModel):
    intake_id: str
    database_name: str
    database_s3_location: str
    database_description: str
    aws_account_id: str
    source_name: str
    enterprise_or_func_name: str
    enterprise_or_func_subgrp_name: str
    region: str
    data_construct: str
    data_env: str
    data_layer: str
    data_leader: str
    data_owner_email: str
    data_owner_github_uname: str
    pr_title: str

    @validator("database_s3_location")
    def s3_must_start(cls, v):
        if not v.startswith("s3://"):
            raise ValueError("S3 path must start with s3://")
        return v

    @validator("aws_account_id")
    def aws_account_valid(cls, v):
        if not v.isdigit() or len(v) != 12:
            raise ValueError("AWS account ID must be 12 digits")
        return v

    @validator("data_owner_email")
    def email_valid(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v


def create_glue_db_pr(input: GlueDBPRInput) -> str:
    try:
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../..")
        )

        yaml_dir = os.path.join(repo_root, "intake_configs")
        yaml_path = os.path.join(
            yaml_dir, f"{input.database_name}.yaml"
        )

        yaml_content = generate_yaml(
            input.dict(exclude={"pr_title"})
        )

        # Commit directly to fork dev
        commit_yaml_to_dev(
            repo_path=repo_root,
            yaml_file_path=yaml_path,
            yaml_content=yaml_content,
        )

        pr = create_pull_request(
            github_token=os.getenv("GITHUB_TOKEN"),
            repo_name=os.getenv("REPO_NAME"),  # upstream repo
            pr_title=input.pr_title,
        )

        return (
            "✅ Pull Request created successfully\n\n"
            f"📁 File: intake_configs/{input.database_name}.yaml\n"
            f"🔗 {pr['html_url']}"
        )

    except Exception as e:
        traceback.print_exc()
        return f"❌ PR Creation Failed\n\nError: {str(e)}"
