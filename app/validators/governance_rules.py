"""
Governance Rules and Validation
Centralized validation rules for enterprise functions, subgroups, and naming conventions
"""

from typing import Dict, List, Optional

# ========================================================
# Enterprise Function and Subgroup Mappings
# ========================================================
ENTERPRISE_FUNCTIONS = {
    "AGTR": "Ag & Trading",
    "CORP": "Corporate",
    "FOOD": "Food",
    "SPEC": "Specialized Portfolio"
}

SUBGROUP_MAPPINGS = {
    # Ag & Trading subgroups
    "AGTR": {
        "EMEA": "Ag & Trading / EMEA",
        "NA": "Ag & Trading / NA",
        "LATAM": "Ag & Trading / LATAM",
        "APAC": "Ag & Trading / APAC",
        "WTG": "Ag & Trading / World Trading Group (WTG)",
        "WTG_CDAS": "Ag & Trading / World Trading Group (WTG) - Cargill Data Asset Solution (CDAS)",
        "OT": "Ag & Trading / Ocean Transportation",
        "CRM": "Ag & Trading / CRM (Cargill Risk Management)",
        "TCM": "Ag & Trading / Trade & Capital Markets (TCM)",
        "MET": "Ag & Trading / Metals"
    },
    # Corporate subgroups
    "CORP": {
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
        "FSQR": "Corporate / Food Safety, Quality & Regulatory"
    },
    # Food subgroups
    "FOOD": {
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
        "RD": "Food / R&D (Research & Development)"
    },
    # Specialized Portfolio subgroups
    "SPEC": {
        "ANH": "Specialized Portfolio / Animal Nutrition",
        "CBI": "Specialized Portfolio / Bioindustrial (CBI)",
        "DS": "Specialized Portfolio / Deicing Solution"
    }
}

# ========================================================
# Valid Values for Glue Database
# ========================================================
VALID_DATA_LAYERS = ["raw", "cln", "curated", "analytics"]
VALID_DATA_ENVS = ["prd", "dev", "staging", "uat"]
VALID_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]

# ========================================================
# Valid Values for S3 Buckets
# ========================================================
VALID_USAGE_TYPES = ["DataProduct", "Logging", "Archive", "Analytics", "Backup"]

# ========================================================
# Naming Convention Patterns
# ========================================================
DATABASE_NAME_PATTERNS = ["minerva_", "cargill_", "data_"]
BUCKET_NAME_PATTERNS = ["minerva-", "cargill-", "data-"]


# ========================================================
# Validation Functions
# ========================================================

def validate_enterprise_function(function_code: str) -> tuple[bool, Optional[str]]:
    """
    Validate enterprise function code

    Returns:
        (is_valid, error_message)
    """
    if function_code not in ENTERPRISE_FUNCTIONS:
        valid_codes = ", ".join(ENTERPRISE_FUNCTIONS.keys())
        return False, (
            f"Invalid enterprise function: '{function_code}'\n"
            f"Valid options: {valid_codes}\n"
            f"Examples:\n"
            f"  - AGTR: Ag & Trading\n"
            f"  - CORP: Corporate\n"
            f"  - FOOD: Food\n"
            f"  - SPEC: Specialized Portfolio"
        )
    return True, None


def validate_subgroup(function_code: str, subgroup_code: str) -> tuple[bool, Optional[str]]:
    """
    Validate that subgroup belongs to the correct enterprise function

    Returns:
        (is_valid, error_message)
    """
    # First validate the enterprise function
    is_valid, error = validate_enterprise_function(function_code)
    if not is_valid:
        return False, error

    # Check if subgroup is valid for this function
    valid_subgroups = SUBGROUP_MAPPINGS.get(function_code, {})

    if subgroup_code not in valid_subgroups:
        valid_codes = ", ".join(valid_subgroups.keys())
        function_name = ENTERPRISE_FUNCTIONS[function_code]

        return False, (
            f"Invalid subgroup '{subgroup_code}' for enterprise function '{function_code}' ({function_name})\n\n"
            f"Valid subgroups for {function_code}:\n" +
            "\n".join([f"  - {code}: {name}" for code, name in valid_subgroups.items()])
        )

    return True, None


def validate_database_name(database_name: str) -> tuple[bool, Optional[str]]:
    """
    Validate Glue database naming convention

    Database names must start with approved prefixes like minerva_, cargill_, etc.
    """
    if not any(database_name.startswith(prefix) for prefix in DATABASE_NAME_PATTERNS):
        valid_prefixes = ", ".join(DATABASE_NAME_PATTERNS)
        return False, (
            f"Database name '{database_name}' doesn't follow naming convention.\n"
            f"Database names must start with one of: {valid_prefixes}\n"
            f"Examples:\n"
            f"  - minerva_sales_analytics\n"
            f"  - minerva_customer_raw\n"
            f"  - cargill_supply_chain_cln"
        )

    # Check for lowercase and valid characters
    if not database_name.islower() or not database_name.replace('_', '').replace('-', '').isalnum():
        return False, (
            f"Database name '{database_name}' contains invalid characters.\n"
            f"Database names must be lowercase and contain only letters, numbers, underscores, and hyphens."
        )

    return True, None


def validate_data_layer(data_layer: str) -> tuple[bool, Optional[str]]:
    """
    Validate data layer value

    Valid values: raw, cln, curated, analytics
    """
    if data_layer not in VALID_DATA_LAYERS:
        valid_layers = ", ".join(VALID_DATA_LAYERS)
        return False, (
            f"Invalid data layer: '{data_layer}'\n"
            f"Valid options: {valid_layers}\n"
            f"Common values:\n"
            f"  - raw: Raw, unprocessed data\n"
            f"  - cln: Cleaned/cleansed data\n"
            f"  - curated: Business-ready data\n"
            f"  - analytics: Analytics-ready data"
        )
    return True, None


def validate_data_env(data_env: str) -> tuple[bool, Optional[str]]:
    """
    Validate data environment

    Valid values: prd, dev, staging, uat
    """
    if data_env not in VALID_DATA_ENVS:
        valid_envs = ", ".join(VALID_DATA_ENVS)
        return False, (
            f"Invalid environment: '{data_env}'\n"
            f"Valid options: {valid_envs}\n"
            f"Common values:\n"
            f"  - prd: Production\n"
            f"  - dev: Development\n"
            f"  - staging: Staging\n"
            f"  - uat: User Acceptance Testing"
        )
    return True, None


def validate_bucket_name(bucket_name: str) -> tuple[bool, Optional[str]]:
    """
    Validate S3 bucket naming convention

    Bucket names must:
    - Start with approved prefixes (minerva-, cargill-, etc.)
    - Be lowercase
    - Use hyphens (not underscores)
    - Be 3-63 characters
    """
    # Check length
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False, f"Bucket name must be between 3 and 63 characters (got {len(bucket_name)})"

    # Check prefix
    if not any(bucket_name.startswith(prefix) for prefix in BUCKET_NAME_PATTERNS):
        valid_prefixes = ", ".join(BUCKET_NAME_PATTERNS)
        return False, (
            f"Bucket name '{bucket_name}' doesn't follow naming convention.\n"
            f"Bucket names must start with one of: {valid_prefixes}\n"
            f"Examples:\n"
            f"  - minerva-sales-analytics-prd\n"
            f"  - minerva-customer-data-dev\n"
            f"  - cargill-supply-chain-raw"
        )

    # Check for lowercase and hyphens (not underscores)
    if not bucket_name.islower():
        return False, f"Bucket name '{bucket_name}' must be all lowercase"

    if '_' in bucket_name:
        return False, (
            f"Bucket name '{bucket_name}' contains underscores.\n"
            f"S3 bucket names must use hyphens (-) instead of underscores (_)"
        )

    # Check for valid characters
    if not bucket_name.replace('-', '').isalnum():
        return False, (
            f"Bucket name '{bucket_name}' contains invalid characters.\n"
            f"Bucket names can only contain lowercase letters, numbers, and hyphens"
        )

    return True, None


def validate_usage_type(usage_type: str) -> tuple[bool, Optional[str]]:
    """
    Validate S3 bucket usage type
    """
    if usage_type not in VALID_USAGE_TYPES:
        valid_types = ", ".join(VALID_USAGE_TYPES)
        return False, (
            f"Invalid usage type: '{usage_type}'\n"
            f"Valid options: {valid_types}"
        )
    return True, None


def get_valid_subgroups_for_function(function_code: str) -> List[str]:
    """
    Get list of valid subgroup codes for a given enterprise function
    """
    return list(SUBGROUP_MAPPINGS.get(function_code, {}).keys())


def get_subgroup_full_name(function_code: str, subgroup_code: str) -> Optional[str]:
    """
    Get full name of a subgroup
    """
    return SUBGROUP_MAPPINGS.get(function_code, {}).get(subgroup_code)