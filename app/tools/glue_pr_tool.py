"""
Glue Database Tool with Validation Layer
Creates YAML config for Glue databases with enterprise-specific validations
"""

import os
from pydantic import BaseModel, Field, validator
from typing import Dict, List

# =========================================================
# Validation Data Structures
# =========================================================

VALID_ENTERPRISE_FUNCTIONS = {
    "AGTR": "Ag & Trading",
    "CORP": "Corporate",
    "FOOD": "Food",
    "SPEC": "Specialized Portfolio"
}

VALID_SUBGROUPS = {
    # Ag & Trading subgroups
    "AGTR": ["EMEA", "NA", "LATAM", "APAC", "WTG", "WTG_CDAS", "OT", "CRM", "TCM", "MET"],

    # Corporate subgroups
    "CORP": ["GI_SUST", "EHS", "FIN", "GTC", "CPT", "HR", "AUDIT", "DTD", "LAW",
             "DTD_DPE", "RMG", "FSQR"],

    # Food subgroups
    "FOOD": ["FSGL", "FS_NA", "FS_LATAM", "FS_APAC", "FS_EMEA", "PRGL", "PR_LATAM",
             "PR_NA", "PR_APAC", "SALT", "CE", "RD"],

    # Specialized Portfolio subgroups
    "SPEC": ["ANH", "CBI", "DS"]
}

SUBGROUP_DESCRIPTIONS = {
    # Ag & Trading
    "EMEA": "Ag & Trading / EMEA",
    "NA": "Ag & Trading / NA",
    "LATAM": "Ag & Trading / LATAM",
    "APAC": "Ag & Trading / APAC",
    "WTG": "Ag & Trading / World Trading Group (WTG)",
    "WTG_CDAS": "Ag & Trading / World Trading Group (WTG) - Cargill Data Asset Solution (CDAS)",
    "OT": "Ag & Trading / Ocean Transportation",
    "CRM": "Ag & Trading / CRM (Cargill Risk Management)",
    "TCM": "Ag & Trading / Trade & Capital Markets (TCM)",
    "MET": "Ag & Trading / Metals",

    # Corporate
    "GI_SUST": "Corporate / Global Impact - Sustainability",
    "EHS": "Corporate / Environment, Health & Safety (EHS)",
    "FIN": "Corporate / Finance",
    "GTC": "Corporate / Global Trade Compliance",
    "CPT": "Corporate / Procurement & Transportation",
    "HR": "Corporate / Human Resources",
    "AUDIT": "Corporate / Audit",
    "DTD": "Corporate / Digital Technology & Data",
    "LAW": "Corporate / Law",
    "DTD_DPE": "Corporate / Digital Technology & Data - Data Platforms & Engineering",
    "RMG": "Corporate / Risk Management Group",
    "FSQR": "Corporate / Food Safety, Quality & Regulatory",

    # Food
    "FSGL": "Food / Food Solutions - All Regions - Global",
    "FS_NA": "Food / Food Solutions - NA",
    "FS_LATAM": "Food / Food Solutions - LATAM",
    "FS_APAC": "Food / Food Solutions - APAC",
    "FS_EMEA": "Food / Food Solutions - EMEA",
    "PRGL": "Food / Protein - All Regions - Global",
    "PR_LATAM": "Food / Protein - LATAM",
    "PR_NA": "Food / Protein - NA",
    "PR_APAC": "Food / Protein - APAC",
    "SALT": "Food / Salt",
    "CE": "Food / Commercial Excellence",
    "RD": "Food / R&D (Research & Development)",

    # Specialized Portfolio
    "ANH": "Specialized Portfolio / Animal Nutrition",
    "CBI": "Specialized Portfolio / Bioindustrial (CBI)",
    "DS": "Specialized Portfolio / Deicing Solution"
}

VALID_ENVIRONMENTS = ["dev", "prd"]
VALID_DATA_LAYERS = ["raw", "cln"]  # data_layer is used as data_classifier


class GlueDBPRInput(BaseModel):
    """
    Input schema for Glue Database configuration with validation layer
    """
    intake_id: str = Field(
        ...,
        description="Unique identifier for this intake request"
    )
    database_name: str = Field(
        ...,
        description="Name of the Glue database (should start with 'minerva')"
    )
    database_s3_location: str = Field(
        ...,
        description="S3 path where database data is stored"
    )
    database_description: str = Field(
        ...,
        description="Brief description of the database purpose"
    )
    aws_account_id: str = Field(
        ...,
        description="AWS account ID (12 digits)"
    )
    source_name: str = Field(
        ...,
        description="Source system name"
    )
    enterprise_or_func_name: str = Field(
        ...,
        description="Enterprise or functional area name (AGTR, CORP, FOOD, SPEC)"
    )
    enterprise_or_func_subgrp_name: str = Field(
        ...,
        description="Sub-group within the enterprise/functional area"
    )
    region: str = Field(
        ...,
        description="AWS region (e.g., us-east-1, us-west-2)"
    )
    data_construct: str = Field(
        ...,
        description="Data construct type"
    )
    data_env: str = Field(
        ...,
        description="Environment (dev or prd)"
    )
    data_layer: str = Field(
        ...,
        description="Data layer/classifier (raw or cln)"
    )
    data_leader: str = Field(
        ...,
        description="Name of the data leader/owner"
    )
    data_owner_email: str = Field(
        ...,
        description="Email address of the data owner"
    )
    data_owner_github_uname: str = Field(
        ...,
        description="GitHub username of the data owner"
    )

    @validator("database_name")
    def validate_database_name(cls, v):
        """Validate that database name starts with 'minerva'"""
        if not v.lower().startswith("minerva"):
            raise ValueError(
                f"Database name must start with 'minerva' (case-insensitive). "
                f"Got: '{v}'"
            )
        return v

    @validator("database_s3_location")
    def validate_s3_location(cls, v):
        """Validate S3 path format"""
        if not v.startswith("s3://"):
            raise ValueError("S3 path must start with 's3://'")
        return v

    @validator("aws_account_id")
    def validate_aws_account(cls, v):
        """Validate AWS account ID is 12 digits"""
        if not v.isdigit() or len(v) != 12:
            raise ValueError("AWS account ID must be exactly 12 digits")
        return v

    @validator("data_owner_email")
    def validate_email(cls, v):
        """Validate email format"""
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email format. Must contain '@' and a domain")
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

    @validator("enterprise_or_func_subgrp_name")
    def validate_subgroup(cls, v, values):
        """Validate subgroup matches the parent enterprise function"""
        # Get the enterprise function (already validated and uppercased)
        enterprise_func = values.get("enterprise_or_func_name")

        if not enterprise_func:
            raise ValueError("Enterprise function must be set before subgroup")

        v_upper = v.upper()

        # Check if subgroup is valid for the parent enterprise function
        valid_subgroups = VALID_SUBGROUPS.get(enterprise_func, [])

        if v_upper not in valid_subgroups:
            raise ValueError(
                f"Invalid subgroup '{v}' for enterprise function '{enterprise_func}'.\n\n"
                f"Valid subgroups for {enterprise_func} ({VALID_ENTERPRISE_FUNCTIONS[enterprise_func]}):\n" +
                "\n".join([f"  - {sg}: {SUBGROUP_DESCRIPTIONS.get(sg, sg)}"
                          for sg in valid_subgroups])
            )

        return v_upper

    @validator("data_env")
    def validate_environment(cls, v):
        """Validate environment is dev or prd"""
        v_lower = v.lower()
        if v_lower not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{v}'. Must be one of: {', '.join(VALID_ENVIRONMENTS)}"
            )
        return v_lower

    @validator("data_layer")
    def validate_data_layer(cls, v):
        """Validate data layer/classifier is raw or cln"""
        v_lower = v.lower()
        if v_lower not in VALID_DATA_LAYERS:
            raise ValueError(
                f"Invalid data layer '{v}'. Must be one of: {', '.join(VALID_DATA_LAYERS)} "
                f"(raw = raw data, cln = cleaned/curated data)"
            )
        return v_lower

    @validator("region")
    def validate_region(cls, v):
        """Validate AWS region format"""
        # Common AWS regions
        common_regions = [
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-central-1",
            "ap-southeast-1", "ap-southeast-2", "ap-northeast-1"
        ]

        # Check basic format: xx-xxxx-#
        if not v or len(v) < 9:
            raise ValueError(
                f"Invalid AWS region format '{v}'. "
                f"Expected format like 'us-east-1'. "
                f"Common regions: {', '.join(common_regions[:5])}"
            )

        return v


def create_glue_db_yaml(input: GlueDBPRInput) -> dict:
    """
    Create Glue Database configuration dictionary
    This will be saved ONLY in the glue_databases folder

    Args:
        input: GlueDBPRInput with validated fields

    Returns:
        Dictionary ready for YAML conversion with resource_type specified
    """
    return {
        "resource_type": "glue_database",
        "intake_id": input.intake_id,
        "database_name": input.database_name,
        "database_s3_location": input.database_s3_location,
        "database_description": input.database_description,
        "aws_account_id": input.aws_account_id,
        "source_name": input.source_name,
        "enterprise_or_func_name": input.enterprise_or_func_name,
        "enterprise_or_func_subgrp_name": input.enterprise_or_func_subgrp_name,
        "region": input.region,
        "data_construct": input.data_construct,
        "data_env": input.data_env,
        "data_layer": input.data_layer,
        "data_leader": input.data_leader,
        "data_owner_email": input.data_owner_email,
        "data_owner_github_uname": input.data_owner_github_uname,
    }


def get_glue_db_file_path(database_name: str, base_path: str = "intake_configs") -> str:
    """
    Generate the correct file path for Glue database YAML
    Ensures file goes into glue_databases folder ONLY

    Args:
        database_name: Name of the database
        base_path: Base directory for configs

    Returns:
        Full path where the YAML should be saved
    """
    glue_db_folder = os.path.join(base_path, "glue_databases")
    os.makedirs(glue_db_folder, exist_ok=True)

    filename = f"{database_name}.yaml"
    return os.path.join(glue_db_folder, filename)


def get_validation_help() -> str:
    """
    Return helpful validation information for users

    Returns:
        Formatted string with validation rules
    """
    return """
📋 GLUE DATABASE VALIDATION RULES:

1. database_name: Must start with 'minerva'
   ✓ Example: minerva_dev_sales_db

2. enterprise_or_func_name: Must be one of:
   • AGTR: Ag & Trading
   • CORP: Corporate
   • FOOD: Food
   • SPEC: Specialized Portfolio

3. enterprise_or_func_subgrp_name: Must match parent function:

   AGTR → EMEA, NA, LATAM, APAC, WTG, WTG_CDAS, OT, CRM, TCM, MET
   CORP → GI_SUST, EHS, FIN, GTC, CPT, HR, AUDIT, DTD, LAW, DTD_DPE, RMG, FSQR
   FOOD → FSGL, FS_NA, FS_LATAM, FS_APAC, FS_EMEA, PRGL, PR_LATAM, PR_NA, PR_APAC, SALT, CE, RD
   SPEC → ANH, CBI, DS

4. data_env: Must be 'dev' or 'prd'

5. data_layer: Must be 'raw' or 'cln'
   • raw = raw data
   • cln = cleaned/curated data

6. aws_account_id: Must be exactly 12 digits

7. data_owner_email: Must be valid email format

8. database_s3_location: Must start with 's3://'
"""