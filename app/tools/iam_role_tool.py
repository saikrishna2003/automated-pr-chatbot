"""
IAM Role Tool
Creates YAML config for IAM roles
"""

import os
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any


class AccessToResources(BaseModel):
    """
    Nested model for access_to_resources
    """
    glue_databases: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Glue database access permissions"
    )
    execution_asset_prefixes: Optional[List[str]] = Field(
        default=None,
        description="S3 prefixes for execution assets"
    )
    glue_crawler: Optional[List[Any]] = Field(
        default=None,
        description="Glue crawler configurations"
    )


class JobControlConfig(BaseModel):
    """
    Job control configuration items
    """
    config_name: str = Field(
        ...,
        description="Configuration name (e.g., agtr_apac)"
    )


class GlueJobAccessConfigs(BaseModel):
    """
    Glue job access configurations
    """
    enable_glue_jobs: bool = Field(
        default=False,
        description="Enable Glue jobs access"
    )
    secret_region: Optional[str] = Field(
        default=None,
        description="AWS region for secrets"
    )
    secret_name: Optional[str] = Field(
        default=None,
        description="Secret name in AWS Secrets Manager"
    )
    job_control_configs: Optional[List[str]] = Field(
        default=None,
        description="List of job control configuration names"
    )


class IAMRolePRInput(BaseModel):
    """
    Input schema for IAM Role configuration
    All fields marked as mandatory except glue_crawler, glue_job_access_configs, and athena
    """
    # Mandatory fields
    intake_id: str = Field(
        ...,
        description="Unique identifier for this intake request"
    )
    role_name: str = Field(
        ...,
        description="Name of the IAM role"
    )
    role_description: str = Field(
        ...,
        description="Description of the IAM role purpose"
    )
    aws_account_id: str = Field(
        ...,
        description="AWS account ID (12 digits)"
    )
    enterprise_or_func_name: str = Field(
        ...,
        description="Enterprise or functional area name"
    )
    enterprise_or_func_subgrp_name: str = Field(
        ...,
        description="Sub-group within the enterprise/functional area"
    )
    role_owner: str = Field(
        ...,
        description="Email address of the role owner"
    )
    data_env: str = Field(
        ...,
        description="Environment (e.g., dev, staging, prod)"
    )
    usage_type: str = Field(
        ...,
        description="Usage type (e.g., EgressEngineer, DataScientist)"
    )
    compute_size: str = Field(
        ...,
        description="Compute size (e.g., XSML, SML, MED, LRG)"
    )
    max_session_duration: int = Field(
        ...,
        description="Maximum session duration in hours"
    )
    access_to_resources: AccessToResources = Field(
        ...,
        description="Resource access configurations"
    )

    # Optional fields (non-mandatory)
    glue_crawler: Optional[List[Any]] = Field(
        default=None,
        description="Glue crawler configurations (optional)"
    )
    glue_job_access_configs: Optional[GlueJobAccessConfigs] = Field(
        default=None,
        description="Glue job access configurations (optional)"
    )
    athena: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Athena configurations (optional)"
    )

    @validator("aws_account_id")
    def aws_account_valid(cls, v):
        if not v.isdigit() or len(v) != 12:
            raise ValueError("AWS account ID must be 12 digits")
        return v

    @validator("role_owner")
    def email_valid(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @validator("max_session_duration")
    def session_duration_valid(cls, v):
        if v < 1 or v > 12:
            raise ValueError("Max session duration must be between 1 and 12 hours")
        return v


def create_iam_role_yaml(input: IAMRolePRInput) -> dict:
    """
    Create IAM Role configuration dictionary
    This will be saved ONLY in the iam_roles folder

    Args:
        input: IAMRolePRInput with validated fields

    Returns:
        Dictionary ready for YAML conversion with resource_type specified
    """
    config = {
        "resource_type": "iam_role",
        "intake_id": input.intake_id,
        "role_name": input.role_name,
        "role_description": input.role_description,
        "aws_account_id": input.aws_account_id,
        "enterprise_or_func_name": input.enterprise_or_func_name,
        "enterprise_or_func_subgrp_name": input.enterprise_or_func_subgrp_name,
        "role_owner": input.role_owner,
        "data_env": input.data_env,
        "usage_type": input.usage_type,
        "compute_size": input.compute_size,
        "max_session_duration": input.max_session_duration,
        "access_to_resources": {}
    }

    # Handle access_to_resources nested structure
    if input.access_to_resources:
        if input.access_to_resources.glue_databases:
            config["access_to_resources"]["glue_databases"] = input.access_to_resources.glue_databases
        if input.access_to_resources.execution_asset_prefixes:
            config["access_to_resources"]["execution_asset_prefixes"] = input.access_to_resources.execution_asset_prefixes
        if input.access_to_resources.glue_crawler:
            config["access_to_resources"]["glue_crawler"] = input.access_to_resources.glue_crawler

    # Add optional fields only if provided
    if input.glue_crawler is not None:
        config["glue_crawler"] = input.glue_crawler

    if input.glue_job_access_configs is not None:
        config["glue_job_access_configs"] = {
            "enable_glue_jobs": input.glue_job_access_configs.enable_glue_jobs
        }
        if input.glue_job_access_configs.secret_region:
            config["glue_job_access_configs"]["secret_region"] = input.glue_job_access_configs.secret_region
        if input.glue_job_access_configs.secret_name:
            config["glue_job_access_configs"]["secret_name"] = input.glue_job_access_configs.secret_name
        if input.glue_job_access_configs.job_control_configs:
            config["glue_job_access_configs"]["job_control_configs"] = input.glue_job_access_configs.job_control_configs

    if input.athena is not None:
        config["athena"] = input.athena

    return config


def get_iam_role_file_path(role_name: str, base_path: str = "intake_configs") -> str:
    """
    Generate the correct file path for IAM role YAML
    Ensures file goes into iam_roles folder ONLY

    Args:
        role_name: Name of the IAM role
        base_path: Base directory for configs

    Returns:
        Full path where the YAML should be saved
    """
    iam_role_folder = os.path.join(base_path, "iam_roles")
    os.makedirs(iam_role_folder, exist_ok=True)

    filename = f"{role_name}.yaml"
    return os.path.join(iam_role_folder, filename) 