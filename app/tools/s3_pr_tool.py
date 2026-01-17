"""
S3 Bucket PR Tool
Creates YAML config for S3 buckets
"""

import os
import re
from pydantic import BaseModel, Field, validator


class S3BucketPRInput(BaseModel):
    """
    Input schema for S3 Bucket PR creation
    Based on the sample YAML provided
    """
    intake_id: str = Field(
        ...,
        description="Unique identifier for the intake request"
    )
    bucket_name: str = Field(
        ...,
        description="Name of the S3 bucket (must follow AWS naming rules)"
    )
    bucket_description: str = Field(
        ...,
        description="Description of the bucket's purpose"
    )
    aws_account_id: str = Field(
        ...,
        description="AWS account ID (12 digits)"
    )
    aws_region: str = Field(
        ...,
        description="AWS region (e.g., us-east-1)"
    )
    usage_type: str = Field(
        ...,
        description="Usage type (e.g., DataProduct, Logging, Archive)"
    )
    enterprise_or_func_name: str = Field(
        ...,
        description="Enterprise or functional area name"
    )

    @validator('bucket_name')
    def validate_bucket_name(cls, v):
        """
        Validate S3 bucket naming rules:
        - 3-63 characters
        - lowercase letters, numbers, hyphens only
        - must start and end with letter or number
        - no underscores
        """
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', v):
            raise ValueError(
                'Bucket name must be lowercase, contain only letters, numbers, and hyphens, '
                'and start/end with a letter or number'
            )
        if len(v) < 3 or len(v) > 63:
            raise ValueError('Bucket name must be between 3 and 63 characters')
        if '_' in v:
            raise ValueError('Bucket name cannot contain underscores (use hyphens instead)')
        return v

    @validator('aws_account_id')
    def validate_aws_account(cls, v):
        """Validate AWS account ID is 12 digits"""
        if not v.isdigit() or len(v) != 12:
            raise ValueError('AWS account ID must be 12 digits')
        return v

    @validator('aws_region')
    def validate_region(cls, v):
        """Basic AWS region validation"""
        valid_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
        ]
        if v not in valid_regions:
            # Warning but don't fail - AWS adds new regions
            print(f"Warning: '{v}' is not a commonly known region")
        return v


def create_s3_bucket_yaml(input: S3BucketPRInput) -> dict:
    """
    Create S3 bucket configuration dictionary

    Args:
        input: S3BucketPRInput with validated fields

    Returns:
        Dictionary ready for YAML conversion
    """
    return {
        "intake_id": input.intake_id,
        "bucket_name": input.bucket_name,
        "bucket_description": input.bucket_description,
        "aws_account_id": input.aws_account_id,
        "aws_region": input.aws_region,
        "usage_type": input.usage_type,
        "enterprise_or_func_name": input.enterprise_or_func_name,
    }