"""
Data Platform Intake Bot - Main API
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
    from prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS
    from tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml
    from tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml
    from services.yaml_generator import generate_yaml
    from services.git_ops import create_pull_request
except ImportError:
    from app.prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS
    from app.tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml
    from app.tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml
    from app.services.yaml_generator import generate_yaml
    from app.services.git_ops import create_pull_request

load_dotenv()

app = FastAPI(title="Data Platform Intake Bot", version="3.0.0")

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
    field_list = GLUE_DB_FIELDS if resource_type == 'glue_db' else S3_BUCKET_FIELDS

    if '\n' in text:
        return parse_key_value(text)
    if ':' in text and text.count(':') >= len(field_list) - 1:
        return parse_key_value(text.replace(',', '\n'))

    return parse_comma_separated(text, field_list)


# =========================================================
# PR Creation
# =========================================================
def create_multi_resource_pr(glue_dbs: List[Dict], s3_buckets: List[Dict], pr_title: str) -> str:
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

        for glue_data in glue_dbs:
            glue_input = GlueDBPRInput(**glue_data)
            yaml_content = generate_yaml(create_glue_db_yaml(glue_input))
            yaml_dir = os.path.join(repo_root, "intake_configs", "glue_databases")
            os.makedirs(yaml_dir, exist_ok=True)
            yaml_path = os.path.join(yaml_dir, f"{glue_input.database_name}.yaml")
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            created_files.append(yaml_path)

        for s3_data in s3_buckets:
            s3_input = S3BucketPRInput(**s3_data)
            yaml_content = generate_yaml(create_s3_bucket_yaml(s3_input))
            yaml_dir = os.path.join(repo_root, "intake_configs", "s3_buckets")
            os.makedirs(yaml_dir, exist_ok=True)
            yaml_path = os.path.join(yaml_dir, f"{s3_input.bucket_name}.yaml")
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            created_files.append(yaml_path)

        repo.index.add(created_files)

        commit_msg = f"{pr_title}\n\n"
        if glue_dbs:
            commit_msg += f"- Added {len(glue_dbs)} Glue Database(s)\n"
        if s3_buckets:
            commit_msg += f"- Added {len(s3_buckets)} S3 Bucket(s)\n"

        repo.index.commit(commit_msg.strip())
        repo.remote("origin").push("dev")

        try:
            pr = create_pull_request(
                github_token=os.getenv("GITHUB_TOKEN1"),
                repo_name=os.getenv("REPO_NAME"),
                pr_title=pr_title,
                pr_body=f"## Resources\n\n"
                        f"{f'- {len(glue_dbs)} Glue DB(s)' if glue_dbs else ''}\n"
                        f"{f'- {len(s3_buckets)} S3 Bucket(s)' if s3_buckets else ''}"
            )

            return (
                f"🎉 Boom! Your PR is live!\n\n"
                f"📋 **Title:** {pr_title}\n"
                f"📦 **What's included:** {len(glue_dbs)} Glue Database(s), {len(s3_buckets)} S3 Bucket(s)\n"
                f"🔗 **View it here:** {pr['html_url']}\n\n"
                f"Great work! Your team can review it whenever they're ready. Need anything else? 😊"
            )

        except RuntimeError as pr_error:
            if "already exists" in str(pr_error).lower():
                return (
                    "🤔 Hmm, looks like you already have a PR open from your fork to upstream!\n\n"
                    "**No worries though!** Your new changes are already committed to your fork's dev branch. "
                    "Here are your options:\n\n"
                    "1️⃣ **Keep the existing PR** - It'll automatically update with your new resources (easiest option!)\n"
                    "2️⃣ **Close the old PR and start fresh** - Let me know and I'll create a brand new one\n\n"
                    "What would you like to do?"
                )
            raise pr_error

    except Exception as e:
        traceback.print_exc()
        return f"❌ Failed: {str(e)}"


# =========================================================
# Session
# =========================================================
session_store = {}

def get_session(sid: str = "default") -> dict:
    if sid not in session_store:
        session_store[sid] = {
            "glue_dbs": [],
            "s3_buckets": [],
            "current_resource_type": None,
            "awaiting_pr_title": False,
            "state": "idle"  # idle, choosing_resource, collecting_data, confirming
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
    return {"status": "online", "service": "Data Platform Intake Bot", "version": "3.0.0"}


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
                    "✨ **S3 Buckets**\n\n"
                    "No more manual YAML editing or Git gymnastics - just chat with me and I'll handle all the technical stuff! 🚀\n\n"
                    "So, what are we building today?"
                )
            )

        user_input = req.messages[-1].get("content", "").strip()
        user_lower = user_input.lower()

        # DIRECT IAM ROLE HANDLER - Bypass LLM for IAM requests
        if any(keyword in user_lower for keyword in ['iam', 'iam role', 'create iam', 'make iam']):
            if not session.get("current_resource_type"):
                session["current_resource_type"] = "iam_role"
                session["state"] = "collecting_data"

                return ChatResponse(
                    response=(
                        "Great! Let's create an IAM role together! 🎯\n\n"
                        "IAM roles need to be provided in **key-value format** (not comma-separated) "
                        "because they have nested structures.\n\n"
                        "Here's the template - just copy this and fill in YOUR values:\n\n"
                        "```\n"
                        "intake_id: INT-1024\n"
                        "role_name: your-role-name-here\n"
                        "role_description: Describe what this role does\n"
                        "aws_account_id: 123456789012\n"
                        "enterprise_or_func_name: YourTeamName\n"
                        "enterprise_or_func_subgrp_name: YourSubTeam\n"
                        "role_owner: your.email@company.com\n"
                        "data_env: dev\n"
                        "usage_type: analytics\n"
                        "compute_size: medium\n"
                        "max_session_duration: 8\n"
                        "access_to_resources:\n"
                        "  glue_databases:\n"
                        "    read:\n"
                        "      - your_database_name\n"
                        "  execution_asset_prefixes:\n"
                        "    - s3://your-bucket/path/\n"
                        "```\n\n"
                        "Just paste this format with your actual values!"
                    )
                )

        # State: Awaiting PR title
        if session.get("awaiting_pr_title"):
            if len(user_input.split()) > 2:
                result = create_multi_resource_pr(
                    glue_dbs=session["glue_dbs"],
                    s3_buckets=session["s3_buckets"],
                    pr_title=user_input
                )
                session_store[req.session_id] = get_session("new")
                return ChatResponse(response=result)

        # State: Collecting data (must have commas or colons and be substantial)
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
                    else:
                        s3 = S3BucketPRInput(**parsed)
                        session["s3_buckets"].append(parsed)
                        name = s3.bucket_name
                        resource_name = "S3 Bucket"

                    session["current_resource_type"] = None
                    session["state"] = "confirming"

                    return ChatResponse(
                        response=(
                            f"✅ Perfect! I've got all the details for your {resource_name} '{name}'.\n\n"
                            f"Want to add more resources to this PR? You can add:\n"
                            f"• Another Glue Database\n"
                            f"• An S3 Bucket\n\n"
                            f"Or just type **'done'** if you're ready to create the PR! 🚀"
                        )
                    )

                except Exception as e:
                    return ChatResponse(response=f"❌ Validation error: {str(e)}\n\nPlease try again.")

        # State: User done collecting
        if "done" in user_lower or ("no" in user_lower and "more" in user_lower):
            if not session["glue_dbs"] and not session["s3_buckets"]:
                return ChatResponse(
                    response="Hmm, we haven't collected any resources yet! Would you like to add a Glue Database or S3 Bucket? 🤔"
                )

            session["awaiting_pr_title"] = True
            return ChatResponse(
                response=(
                    f"Awesome! Here's what we're packaging up:\n"
                    f"📦 {len(session['glue_dbs'])} Glue Database(s)\n"
                    f"📦 {len(session['s3_buckets'])} S3 Bucket(s)\n\n"
                    f"Now, let's give this PR a good title! What should we call it?\n"
                    f"(Something descriptive like 'Add analytics resources for Q1 2025')"
                )
            )

        # LLM conversation with STRICT anti-hallucination prompt
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