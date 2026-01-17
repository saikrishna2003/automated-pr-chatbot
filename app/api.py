"""
Data Platform Intake Bot - Main API
UPDATED: Now supports IAM Roles
STRICT VERSION: No data hallucination allowed
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import traceback
from dotenv import load_dotenv

from langchain_groq import ChatGroq

# Import from local modules
import sys
from pathlib import Path

app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

try:
    from prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS, IAM_ROLE_FIELDS
    from tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml
    from tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml
    from tools.iam_role_tool import IAMRolePRInput, create_iam_role_yaml
    from services.yaml_generator import generate_yaml
    from services.git_ops import create_pull_request
except ImportError:
    from app.prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS, IAM_ROLE_FIELDS
    from app.tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml
    from app.tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml
    from app.tools.iam_role_tool import IAMRolePRInput, create_iam_role_yaml
    from app.services.yaml_generator import generate_yaml
    from app.services.git_ops import create_pull_request

load_dotenv()

app = FastAPI(title="Data Platform Intake Bot", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)

# =========================================================
# Parsing Functions
# =========================================================
def parse_comma_separated(text: str, field_list: List[str]) -> Dict[str, str]:
    values = [v.strip() for v in text.split(",")]
    if len(values) != len(field_list):
        raise ValueError(
            f"Expected {len(field_list)} values but got {len(values)}.\n\n"
            f"Required: {', '.join(field_list)}"
        )
    return dict(zip(field_list, values))


def parse_key_value(text: str) -> Dict[str, str]:
    """
    Parse key-value format input
    Handles both simple and nested YAML structures
    """
    import yaml

    # Try to parse as YAML first for nested structures
    try:
        # Check if it looks like YAML (has proper newlines and indentation)
        if '\n' in text and (':' in text):
            parsed = yaml.safe_load(text)
            if isinstance(parsed, dict):
                return parsed
    except:
        pass

    # Fallback to simple key-value parsing
    result = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result


def smart_parse_input(text: str, resource_type: str) -> Dict[str, str]:
    if resource_type == 'glue_db':
        field_list = GLUE_DB_FIELDS
    elif resource_type == 's3_bucket':
        field_list = S3_BUCKET_FIELDS
    elif resource_type == 'iam_role':
        # IAM roles require special handling due to nested structures
        # For now, we'll only support key-value format for IAM roles
        if '\n' not in text and ':' not in text:
            raise ValueError(
                "IAM roles must be provided in key-value format due to complex nested structures.\n\n"
                "Please provide the data like this:\n"
                "intake_id: INT-901\n"
                "role_name: analytics-readonly-role\n"
                "role_description: Read-only IAM role\n"
                "aws_account_id: 123456789012\n"
                "enterprise_or_func_name: DataPlatform\n"
                "enterprise_or_func_subgrp_name: Analytics\n"
                "role_owner: analytics.owner@company.com\n"
                "data_env: prod\n"
                "usage_type: analytics\n"
                "compute_size: medium\n"
                "max_session_duration: 8\n"
                "access_to_resources:\n"
                "  glue_databases:\n"
                "    read:\n"
                "      - glue_db_sales\n"
                "      - glue_db_marketing\n"
                "  execution_asset_prefixes:\n"
                "    - s3://exec-assets/analytics/\n"
                "    - s3://exec-assets/shared/"
            )
        return parse_key_value(text)
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")

    if '\n' in text:
        return parse_key_value(text)
    if ':' in text and text.count(':') >= len(field_list) - 1:
        return parse_key_value(text.replace(',', '\n'))

    return parse_comma_separated(text, field_list)


# =========================================================
# PR Creation - Supports Glue DB, S3, and IAM Roles
# =========================================================
def create_multi_resource_pr(
    glue_dbs: List[Dict],
    s3_buckets: List[Dict],
    iam_roles: List[Dict],
    pr_title: str
) -> str:
    try:
        from git import Repo

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        repo = Repo(repo_root)
        git = repo.git

        if repo.is_dirty(untracked_files=True):
            untracked = repo.untracked_files
            modified = [item.a_path for item in repo.index.diff(None)]
            all_changes = untracked + modified
            non_intake = [f for f in all_changes if not f.startswith('intake_configs/')]

            if non_intake:
                raise RuntimeError(
                    f"Repository has uncommitted changes: {', '.join(non_intake)}\n"
                    "Please commit or stash them first."
                )

        git.checkout("dev")
        git.pull("origin", "dev")

        created_files = []

        # Create Glue DB files in glue_databases folder
        if glue_dbs:
            glue_db_dir = os.path.join(repo_root, "intake_configs", "glue_databases")
            os.makedirs(glue_db_dir, exist_ok=True)

            for glue_data in glue_dbs:
                glue_input = GlueDBPRInput(**glue_data)
                yaml_content = generate_yaml(create_glue_db_yaml(glue_input))
                yaml_path = os.path.join(glue_db_dir, f"{glue_input.database_name}.yaml")

                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

                created_files.append(yaml_path)
                print(f"✅ Created Glue DB YAML: {yaml_path}")

        # Create S3 bucket files in s3_buckets folder
        if s3_buckets:
            s3_bucket_dir = os.path.join(repo_root, "intake_configs", "s3_buckets")
            os.makedirs(s3_bucket_dir, exist_ok=True)

            for s3_data in s3_buckets:
                s3_input = S3BucketPRInput(**s3_data)
                yaml_content = generate_yaml(create_s3_bucket_yaml(s3_input))
                yaml_path = os.path.join(s3_bucket_dir, f"{s3_input.bucket_name}.yaml")

                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

                created_files.append(yaml_path)
                print(f"✅ Created S3 Bucket YAML: {yaml_path}")

        # Create IAM role files in iam_roles folder
        if iam_roles:
            iam_role_dir = os.path.join(repo_root, "intake_configs", "iam_roles")
            os.makedirs(iam_role_dir, exist_ok=True)

            for iam_data in iam_roles:
                iam_input = IAMRolePRInput(**iam_data)
                yaml_content = generate_yaml(create_iam_role_yaml(iam_input))
                yaml_path = os.path.join(iam_role_dir, f"{iam_input.role_name}.yaml")

                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

                created_files.append(yaml_path)
                print(f"✅ Created IAM Role YAML: {yaml_path}")

        # Add all created files to git
        repo.index.add(created_files)

        commit_msg = f"{pr_title}\n\n"
        if glue_dbs:
            commit_msg += f"- Added {len(glue_dbs)} Glue Database(s)\n"
        if s3_buckets:
            commit_msg += f"- Added {len(s3_buckets)} S3 Bucket(s)\n"
        if iam_roles:
            commit_msg += f"- Added {len(iam_roles)} IAM Role(s)\n"

        repo.index.commit(commit_msg.strip())
        repo.remote("origin").push("dev")

        try:
            pr = create_pull_request(
                github_token=os.getenv("GITHUB_TOKEN1"),
                repo_name=os.getenv("REPO_NAME"),
                pr_title=pr_title,
                pr_body=f"## Resources\n\n"
                        f"{f'- {len(glue_dbs)} Glue DB(s)' if glue_dbs else ''}\n"
                        f"{f'- {len(s3_buckets)} S3 Bucket(s)' if s3_buckets else ''}\n"
                        f"{f'- {len(iam_roles)} IAM Role(s)' if iam_roles else ''}"
            )

            return (
                f"✅ PR created successfully!\n\n"
                f"📋 {pr_title}\n"
                f"📁 {len(glue_dbs)} Glue DB(s), {len(s3_buckets)} S3 Bucket(s), {len(iam_roles)} IAM Role(s)\n"
                f"🔗 {pr['html_url']}"
            )

        except RuntimeError as pr_error:
            if "already exists" in str(pr_error).lower():
                return (
                    "⚠️ A PR already exists from your fork's dev to upstream dev.\n\n"
                    "Options:\n"
                    "1. Close the existing PR and create a new one\n"
                    "2. Add to existing PR (changes already committed to your fork)\n\n"
                    "Which would you prefer?"
                )
            raise pr_error

    except Exception as e:
        traceback.print_exc()
        return f"❌ Failed: {str(e)}"


# =========================================================
# Session - Updated to track IAM roles
# =========================================================
session_store = {}

def get_session(sid: str = "default") -> dict:
    if sid not in session_store:
        session_store[sid] = {
            "glue_dbs": [],
            "s3_buckets": [],
            "iam_roles": [],  # NEW
            "current_resource_type": None,
            "awaiting_pr_title": False,
            "state": "idle"
        }
    return session_store[sid]


# =========================================================
# Models
# =========================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str


# =========================================================
# Routes
# =========================================================
@app.get("/")
def root():
    return {"status": "online", "service": "Data Platform Intake Bot", "version": "4.0.0"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        session = get_session(req.session_id)

        if not req.messages:
            return ChatResponse(
                response=(
                    "👋 Hey there! I'm your MIW Data Platform Assistant!\n\n"
                    "I'm here to help you create automated Pull Requests for:\n"
                    "✨ **Glue Databases**\n"
                    "✨ **S3 Buckets**\n"
                    "✨ **IAM Roles**\n\n"
                    "No more manual YAML editing or Git gymnastics - just chat with me and I'll handle all the technical stuff! 🚀\n\n"
                    "So, what are we building today?"
                )
            )

        user_input = req.messages[-1].get("content", "").strip()
        user_lower = user_input.lower()

        # State: Awaiting PR title
        if session.get("awaiting_pr_title"):
            if len(user_input.split()) > 2:
                result = create_multi_resource_pr(
                    glue_dbs=session["glue_dbs"],
                    s3_buckets=session["s3_buckets"],
                    iam_roles=session["iam_roles"],
                    pr_title=user_input
                )
                session_store[req.session_id] = get_session("new")
                return ChatResponse(response=result)

        # State: Collecting data
        has_separators = (',' in user_input or (':' in user_input and '\n' in user_input))
        is_substantial = len(user_input) > 40
        is_not_question = not any(q in user_lower for q in ['what', 'how', 'which', 'prefer', '?', 'format', 'option'])

        if has_separators and is_substantial and is_not_question:
            resource_type = session.get("current_resource_type")

            if resource_type:
                try:
                    parsed = smart_parse_input(user_input, resource_type)

                    if resource_type == "glue_db":
                        glue = GlueDBPRInput(**parsed)
                        session["glue_dbs"].append(parsed)
                        name = glue.database_name
                        resource_name = "Glue Database"
                    elif resource_type == "s3_bucket":
                        s3 = S3BucketPRInput(**parsed)
                        session["s3_buckets"].append(parsed)
                        name = s3.bucket_name
                        resource_name = "S3 Bucket"
                    elif resource_type == "iam_role":
                        # IAM roles need special handling for nested structures
                        # For now, require key-value format
                        if ',' in user_input and '\n' not in user_input:
                            return ChatResponse(
                                response=(
                                    "⚠️ IAM roles have complex nested structures and require **key-value format**.\n\n"
                                    "Please provide the data in this format:\n\n"
                                    "```\n"
                                    "intake_id: INT-901\n"
                                    "role_name: analytics-readonly-role\n"
                                    "role_description: Read-only IAM role for analytics\n"
                                    "aws_account_id: 123456789012\n"
                                    "enterprise_or_func_name: DataPlatform\n"
                                    "enterprise_or_func_subgrp_name: Analytics\n"
                                    "role_owner: analytics.owner@company.com\n"
                                    "data_env: prod\n"
                                    "usage_type: analytics\n"
                                    "compute_size: medium\n"
                                    "max_session_duration: 8\n"
                                    "access_to_resources:\n"
                                    "  glue_databases:\n"
                                    "    read:\n"
                                    "      - glue_db_sales\n"
                                    "      - glue_db_marketing\n"
                                    "  execution_asset_prefixes:\n"
                                    "    - s3://exec-assets/analytics/\n"
                                    "    - s3://exec-assets/shared/\n"
                                    "```\n\n"
                                    "Copy-paste this format and fill in your values!"
                                )
                            )

                        iam = IAMRolePRInput(**parsed)
                        session["iam_roles"].append(parsed)
                        name = iam.role_name
                        resource_name = "IAM Role"

                    session["current_resource_type"] = None
                    session["state"] = "confirming"

                    return ChatResponse(
                        response=(
                            f"✅ Got it! Collected {resource_name} '{name}'.\n\n"
                            "Add another resource? (Glue Database, S3 Bucket, or IAM Role)\n"
                            "Or type 'done' to create the PR."
                        )
                    )

                except Exception as e:
                    return ChatResponse(response=f"❌ Validation error: {str(e)}\n\nPlease try again.")

        # State: User done collecting
        if "done" in user_lower or ("no" in user_lower and "more" in user_lower):
            if not session["glue_dbs"] and not session["s3_buckets"] and not session["iam_roles"]:
                return ChatResponse(response="No resources added yet. Add a Glue Database, S3 Bucket, or IAM Role?")

            session["awaiting_pr_title"] = True
            return ChatResponse(
                response=(
                    f"Perfect! You have:\n"
                    f"- {len(session['glue_dbs'])} Glue DB(s)\n"
                    f"- {len(session['s3_buckets'])} S3 Bucket(s)\n"
                    f"- {len(session['iam_roles'])} IAM Role(s)\n\n"
                    "What should the PR title be?"
                )
            )

        # LLM conversation
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    "ABSOLUTE RULE: You are NOT allowed to generate, invent, create, or make up ANY data values. "
                    "If the user has not provided actual field values yet, you MUST ask them to provide the values. "
                    "DO NOT show example values. DO NOT pretend you received data. "
                    "ONLY confirm data collection AFTER the user has provided actual values in comma-separated or key-value format."
                )
            }
        ]
        messages.extend(req.messages)

        llm_response = llm.invoke(messages)

        # Track resource type
        resp_lower = llm_response.content.lower()
        if "glue" in resp_lower and ("database" in resp_lower or "db" in resp_lower):
            session["current_resource_type"] = "glue_db"
            session["state"] = "collecting_data"
        elif "s3" in resp_lower and "bucket" in resp_lower:
            session["current_resource_type"] = "s3_bucket"
            session["state"] = "collecting_data"
        elif "iam" in resp_lower and "role" in resp_lower:
            session["current_resource_type"] = "iam_role"
            session["state"] = "collecting_data"

        return ChatResponse(response=llm_response.content)

    except Exception as e:
        traceback.print_exc()
        return ChatResponse(response=f"❌ Error: {str(e)}")


@app.post("/reset")
def reset(session_id: str = "default"):
    if session_id in session_store:
        del session_store[session_id]
    return {"status": "reset"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "github": bool(os.getenv("GITHUB_TOKEN1")),
        "username": bool(os.getenv("GITHUB_USERNAME")),
    }