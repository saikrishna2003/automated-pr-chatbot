"""
Data Platform Intake Bot - Main API
Multi-resource PR creation with flexible input formats
"""

from fastapi import FastAPI, HTTPException
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

# Ensure app directory is in path
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
    # Fallback to app. prefix
    from app.prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS
    from app.tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml
    from app.tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml
    from app.services.yaml_generator import generate_yaml
    from app.services.git_ops import create_pull_request

# =========================================================
# ENV
# =========================================================
load_dotenv()

# =========================================================
# APP
# =========================================================
app = FastAPI(
    title="Data Platform Intake Bot",
    version="3.0.0",
    description="Multi-resource PR creation with flexible input"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# LLM
# =========================================================
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.1,
)

# =========================================================
# Input Parsing
# =========================================================
def parse_comma_separated(text: str, field_list: List[str]) -> Dict[str, str]:
    """Parse comma-separated input"""
    values = [v.strip() for v in text.split(",")]

    if len(values) != len(field_list):
        raise ValueError(
            f"Expected {len(field_list)} values but got {len(values)}.\n\n"
            f"Required fields: {', '.join(field_list)}"
        )

    return dict(zip(field_list, values))


def parse_key_value(text: str) -> Dict[str, str]:
    """Parse key-value input (YAML-like or key: value format)"""
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
    """
    Intelligently parse user input in either format
    """
    field_list = GLUE_DB_FIELDS if resource_type == 'glue_db' else S3_BUCKET_FIELDS

    # Check if input contains newlines (key-value format)
    if '\n' in text:
        return parse_key_value(text)

    # Check if input has many colons (single-line key-value)
    if ':' in text and text.count(':') > 2:
        return parse_key_value(text.replace(',', '\n'))

    # Otherwise, assume comma-separated
    return parse_comma_separated(text, field_list)


# =========================================================
# PR Creation
# =========================================================
def create_multi_resource_pr(
    glue_dbs: List[Dict],
    s3_buckets: List[Dict],
    pr_title: str
) -> str:
    """Create a single PR with multiple resources"""
    try:
        from git import Repo

        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        repo = Repo(repo_root)
        git = repo.git

        # Ensure clean state
        if repo.is_dirty(untracked_files=True):
            untracked = repo.untracked_files
            modified = [item.a_path for item in repo.index.diff(None)]

            # Check if changes are only in intake_configs
            all_changes = untracked + modified
            non_intake = [f for f in all_changes if not f.startswith('intake_configs/')]

            if non_intake:
                raise RuntimeError(
                    f"Repository has uncommitted changes: {', '.join(non_intake)}\n"
                    "Please commit or stash them first."
                )

        # Checkout dev
        git.checkout("dev")
        git.pull("origin", "dev")

        created_files = []

        # Create Glue DB YAML files
        for glue_data in glue_dbs:
            glue_input = GlueDBPRInput(**glue_data)
            yaml_content = generate_yaml(create_glue_db_yaml(glue_input))

            yaml_dir = os.path.join(repo_root, "intake_configs", "glue_databases")
            os.makedirs(yaml_dir, exist_ok=True)

            yaml_path = os.path.join(yaml_dir, f"{glue_input.database_name}.yaml")

            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)

            created_files.append(yaml_path)

        # Create S3 Bucket YAML files
        for s3_data in s3_buckets:
            s3_input = S3BucketPRInput(**s3_data)
            yaml_content = generate_yaml(create_s3_bucket_yaml(s3_input))

            yaml_dir = os.path.join(repo_root, "intake_configs", "s3_buckets")
            os.makedirs(yaml_dir, exist_ok=True)

            yaml_path = os.path.join(yaml_dir, f"{s3_input.bucket_name}.yaml")

            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)

            created_files.append(yaml_path)

        # Stage and commit
        repo.index.add(created_files)

        commit_msg = f"{pr_title}\n\n"
        if glue_dbs:
            commit_msg += f"- Added {len(glue_dbs)} Glue Database(s)\n"
        if s3_buckets:
            commit_msg += f"- Added {len(s3_buckets)} S3 Bucket(s)\n"

        repo.index.commit(commit_msg.strip())
        repo.remote("origin").push("dev")

        # Create PR
        try:
            pr = create_pull_request(
                github_token=os.getenv("GITHUB_TOKEN1"),
                repo_name=os.getenv("REPO_NAME"),
                pr_title=pr_title,
                pr_body=f"## Resources Added\n\n"
                        f"{'- ' + str(len(glue_dbs)) + ' Glue Database(s)' if glue_dbs else ''}\n"
                        f"{'- ' + str(len(s3_buckets)) + ' S3 Bucket(s)' if s3_buckets else ''}"
            )

            return (
                f"✅ Pull Request created successfully!\n\n"
                f"📋 Title: {pr_title}\n"
                f"📁 Resources: {len(glue_dbs)} Glue DB(s), {len(s3_buckets)} S3 Bucket(s)\n"
                f"🔗 {pr['html_url']}"
            )

        except RuntimeError as pr_error:
            error_msg = str(pr_error)

            if "already exists" in error_msg.lower():
                return (
                    "⚠️ A Pull Request already exists from your fork's dev branch to upstream dev.\n\n"
                    "You have two options:\n"
                    "1. **Close the existing PR** and I'll create a new one with these resources\n"
                    "2. **Add to the existing PR** - I've already committed your changes to your fork's dev branch. "
                    "The existing PR will automatically update with these new resources.\n\n"
                    "Which would you prefer?"
                )
            else:
                raise pr_error

    except Exception as e:
        traceback.print_exc()
        return f"❌ Failed to create PR\n\nError: {str(e)}"


# =========================================================
# Session Management
# =========================================================
session_store = {}

def get_session(session_id: str = "default") -> dict:
    """Get or create session"""
    if session_id not in session_store:
        session_store[session_id] = {
            "glue_dbs": [],
            "s3_buckets": [],
            "pr_title": None,
            "current_resource_type": None,
            "awaiting_pr_title": False
        }
    return session_store[session_id]


# =========================================================
# Models
# =========================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    session: Optional[Dict] = None


# =========================================================
# Routes
# =========================================================
@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Data Platform Intake Bot",
        "version": "3.0.0",
        "supported_resources": ["glue_database", "s3_bucket"]
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        session = get_session(req.session_id)

        if not req.messages:
            return ChatResponse(
                response="Hi! I can help you create PRs for Glue Databases and S3 Buckets. What would you like to create?",
                session=session
            )

        user_input = req.messages[-1].get("content", "").strip()
        user_input_lower = user_input.lower()

        # Check if awaiting PR title
        if session.get("awaiting_pr_title"):
            if len(user_input.split()) > 2:  # Looks like a title
                result = create_multi_resource_pr(
                    glue_dbs=session["glue_dbs"],
                    s3_buckets=session["s3_buckets"],
                    pr_title=user_input
                )

                # Clear session
                session_store[req.session_id] = {
                    "glue_dbs": [],
                    "s3_buckets": [],
                    "pr_title": None,
                    "current_resource_type": None,
                    "awaiting_pr_title": False
                }

                return ChatResponse(response=result, session=session_store[req.session_id])

        # Check if user is providing resource data
        if any(sep in user_input for sep in [',', ':', '\n']) and len(user_input) > 20:
            resource_type = session.get("current_resource_type")

            if resource_type:
                try:
                    parsed_data = smart_parse_input(user_input, resource_type)

                    if resource_type == "glue_db":
                        glue_input = GlueDBPRInput(**parsed_data)
                        session["glue_dbs"].append(parsed_data)
                        response_text = (
                            f"✅ Got it! I've collected your Glue Database configuration for '{glue_input.database_name}'.\n\n"
                            "Would you like to add another resource to this PR? (Glue Database or S3 Bucket)\n"
                            "Or type 'done' if you're ready to create the PR."
                        )
                    else:  # s3_bucket
                        s3_input = S3BucketPRInput(**parsed_data)
                        session["s3_buckets"].append(parsed_data)
                        response_text = (
                            f"✅ Got it! I've collected your S3 Bucket configuration for '{s3_input.bucket_name}'.\n\n"
                            "Would you like to add another resource to this PR? (Glue Database or S3 Bucket)\n"
                            "Or type 'done' if you're ready to create the PR."
                        )

                    session["current_resource_type"] = None

                    return ChatResponse(response=response_text, session=session)

                except Exception as e:
                    return ChatResponse(
                        response=f"❌ Validation error: {str(e)}\n\nPlease check your input and try again.",
                        session=session
                    )

        # Check if user is done
        if "done" in user_input_lower or ("no" in user_input_lower and ("more" in user_input_lower or "another" in user_input_lower)):
            if not session["glue_dbs"] and not session["s3_buckets"]:
                return ChatResponse(
                    response="You haven't added any resources yet. Would you like to add a Glue Database or S3 Bucket?",
                    session=session
                )

            session["awaiting_pr_title"] = True
            return ChatResponse(
                response=f"Perfect! You have:\n"
                        f"- {len(session['glue_dbs'])} Glue Database(s)\n"
                        f"- {len(session['s3_buckets'])} S3 Bucket(s)\n\n"
                        f"What would you like the PR title to be?",
                session=session
            )

        # Regular LLM conversation
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(req.messages)

        llm_response = llm.invoke(messages)

        # Track resource type for next input
        response_lower = llm_response.content.lower()
        if "glue" in response_lower and "database" in response_lower:
            session["current_resource_type"] = "glue_db"
        elif "s3" in response_lower and "bucket" in response_lower:
            session["current_resource_type"] = "s3_bucket"

        return ChatResponse(
            response=llm_response.content,
            session=session
        )

    except Exception as e:
        traceback.print_exc()
        return ChatResponse(
            response=f"❌ Error: {str(e)}",
            session=get_session(req.session_id)
        )


@app.post("/reset")
def reset_session(session_id: str = "default"):
    """Reset conversation session"""
    if session_id in session_store:
        del session_store[session_id]
    return {"status": "success", "message": "Session reset"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "groq_key": bool(os.getenv("GROQ_API_KEY")),
        "github_token": bool(os.getenv("GITHUB_TOKEN1")),
        "github_username": bool(os.getenv("GITHUB_USERNAME")),
        "repo": os.getenv("REPO_NAME"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)