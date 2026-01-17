"""
S3 Bucket Tool with Validation Layer
Creates YAML config for S3 buckets with enterprise-specific validations
"""

import os
import re
from pydantic import BaseModel, Field, validator

# Same enterprise functions as Glue DB
VALID_ENTERPRISE_FUNCTIONS = {
    "AGTR": "Ag & Trading",
    "CORP": "Corporate",
    "FOOD": "Food",
    "SPEC": "Specialized Portfolio"
}


class S3BucketPRInput(BaseModel):
    """
    Input schema for S3 Bucket with validation layer
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
        description="Enterprise or functional area name (AGTR, CORP, FOOD, SPEC)"
    )

    @validator('bucket_name')
    def validate_bucket_name(cls, v):
        """
        Validate S3 bucket naming rules:
        - 3-63 characters
        - lowercase letters, numbers, hyphens, dots only
        - must start and end with letter or number
        - no underscores
        - no consecutive dots
        """
        if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', v):
            raise ValueError(
                f"Bucket name '{v}' is invalid. Must:\n"
                "- Be lowercase\n"
                "- Contain only letters, numbers, hyphens, and dots\n"
                "- Start and end with a letter or number"
            )

        if len(v) < 3 or len(v) > 63:
            raise ValueError(f"Bucket name must be between 3 and 63 characters. Got {len(v)} characters.")

        if '_' in v:
            raise ValueError("Bucket name cannot contain underscores. Use hyphens (-) instead.")

        if '..' in v:
            raise ValueError("Bucket name cannot contain consecutive dots (..).")

        # Check if it looks like an IP address
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', v):
            raise ValueError("Bucket name cannot be formatted as an IP address.")

        return v.lower()

    @validator('aws_account_id')
    def validate_aws_account(cls, v):
        """Validate AWS account ID is 12 digits"""
        if not v.isdigit() or len(v) != 12:
            raise ValueError('AWS account ID must be exactly 12 digits')
        return v

    @validator('aws_region')
    def validate_region(cls, v):
        """Validate AWS region format"""
        # Common AWS regions
        valid_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-northeast-2',
            'ap-south-1', 'sa-east-1', 'ca-central-1'
        ]

        if v not in valid_regions:
            raise ValueError(
                f"Invalid or uncommon AWS region '{v}'.\n"
                f"Common regions: {', '.join(valid_regions[:8])}"
            )
        return v

    @validator("enterprise_or_func_name")
    def validate_enterprise_function(cls, v):
        """Validate enterprise function is one of the allowed values"""
        v_upper = v.upper()
        if v_upper not in VALID_ENTERPRISE_FUNCTIONS:
            valid_options = ", ".join(VALID_ENTERPRISE_FUNCTIONS.keys())
            raise ValueError(
                f"Invalid enterprise function '{v}'. "
                f"Must be one of: {valid_options}\n\n"
                f"Valid values:\n" +
                "\n".join([f"  - {k}: {desc}" for k, desc in VALID_ENTERPRISE_FUNCTIONS.items()])
            )
        return v_upper


def create_s3_bucket_yaml(input: S3BucketPRInput) -> dict:
    """
    Create S3 bucket configuration dictionary

    Args:
        input: S3BucketPRInput with validated fields

    Returns:
        Dictionary ready for YAML conversion
    """
    return {
        "resource_type": "s3_bucket",
        "intake_id": input.intake_id,
        "bucket_name": input.bucket_name,
        "bucket_description": input.bucket_description,
        "aws_account_id": input.aws_account_id,
        "aws_region": input.aws_region,
        "usage_type": input.usage_type,
        "enterprise_or_func_name": input.enterprise_or_func_name,
    }


def get_s3_bucket_file_path(bucket_name: str, base_path: str = "intake_configs") -> str:
    """
    Generate the correct file path for S3 bucket YAML
    Ensures file goes into s3_buckets folder ONLY

    Args:
        bucket_name: Name of the bucket
        base_path: Base directory for configs

    Returns:
        Full path where the YAML should be saved
    """
    s3_bucket_folder = os.path.join(base_path, "s3_buckets")
    os.makedirs(s3_bucket_folder, exist_ok=True)

    filename = f"{bucket_name}.yaml"
    return os.path.join(s3_bucket_folder, filename)


def get_s3_validation_help() -> str:
    """
    Return helpful validation information for S3 buckets

    Returns:
        Formatted string with validation rules
    """
    return """
📋 S3 BUCKET VALIDATION RULES:

1. bucket_name: Must follow AWS naming rules
   ✓ 3-63 characters long
   ✓ Lowercase letters, numbers, hyphens (-), and dots (.)
   ✓ Start and end with letter or number
   ✗ No underscores (_)
   ✗ No consecutive dots (..)
   ✗ Cannot look like an IP address (e.g., 192.168.1.1)

   Example: my-data-bucket-2024 ✓
   Example: My_Bucket ✗ (uppercase and underscore)

2. enterprise_or_func_name: Must be one of:
   • AGTR: Ag & Trading
   • CORP: Corporate
   • FOOD: Food
   • SPEC: Specialized Portfolio

3. aws_account_id: Must be exactly 12 digits

4. aws_region: Must be a valid AWS region
   Common: us-east-1, us-west-2, eu-west-1, ap-southeast-1
"""