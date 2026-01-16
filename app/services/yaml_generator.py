"""
YAML Generator Service
Converts dictionary data to YAML format for configuration files
"""

import yaml
from typing import Dict, Any


def generate_yaml(data: Dict[str, Any]) -> str:
    """
    Generate YAML content from dictionary data

    Args:
        data: Dictionary containing configuration data

    Returns:
        YAML formatted string

    Example:
        >>> data = {"database_name": "my_db", "region": "us-east-1"}
        >>> yaml_str = generate_yaml(data)
        >>> print(yaml_str)
        database_name: my_db
        region: us-east-1
    """
    return yaml.dump(
        data,
        sort_keys=False,  # Preserve insertion order
        default_flow_style=False,  # Use block style (not inline)
        allow_unicode=True,  # Support Unicode characters
        indent=2  # Use 2-space indentation
    )


def generate_yaml_with_comments(data: Dict[str, Any], comments: Dict[str, str] = None) -> str:
    """
    Generate YAML with optional inline comments

    Args:
        data: Dictionary containing configuration data
        comments: Optional dictionary mapping field names to comment strings

    Returns:
        YAML formatted string with comments

    Example:
        >>> data = {"database_name": "my_db", "region": "us-east-1"}
        >>> comments = {"database_name": "Name of the Glue database"}
        >>> yaml_str = generate_yaml_with_comments(data, comments)
    """
    if comments is None:
        return generate_yaml(data)

    # Generate base YAML
    yaml_lines = generate_yaml(data).split('\n')

    # Add comments where applicable
    result_lines = []
    for line in yaml_lines:
        if ':' in line:
            key = line.split(':')[0].strip()
            if key in comments:
                result_lines.append(f"{line}  # {comments[key]}")
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)

    return '\n'.join(result_lines)