"""
Data Platform Intake Bot - Main API
Stable version with bulk comma-separated input support
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import traceback
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from app.tools.glue_pr_tool import create_glue_db_pr, GlueDBPRInput

# =========================================================
# ENV
# =========================================================
load_dotenv()

# =========================================================
# APP
# =========================================================
app = FastAPI(
    title="Data Platform Intake Bot",
    version="2.0.0",
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
# SYSTEM PROMPT (FULL – NOT REMOVED)
# =========================================================
SYSTEM_PROMPT = """You are the Data Platform Intake Bot, a helpful assistant that creates automated Pull Requests for Glue Database configurations.

YOUR CAPABILITIES:
- You help users create Glue Database Pull Requests
- You collect required information through natural conversation
- You create PRs automatically when all information is gathered

CONVERSATION RULES:
- When the user asks to create a Glue DB PR, LIST ALL REQUIRED FIELDS at once
- Ask the user to provide values in a SINGLE comma-separated line
- Do NOT ask questions one-by-one
- Do NOT reorder fields
- After receiving comma-separated input:
  - Parse it in order
  - Validate fields
  - Call the PR creation tool if all fields are present
- If the number of values is incorrect, explain the expected format clearly
- Never mention tools, functions, or internal code

INFORMATION TO COLLECT (16 fields required):
When a user wants to create a Glue Database PR, you need to collect:

1. intake_id - Unique identifier for this intake request
2. database_name - Name of the Glue database
3. database_s3_location - S3 path where database data is stored (format: s3://bucket/path)
4. database_description - Brief description of the database purpose
5. aws_account_id - AWS account ID (12 digits)
6. source_name - Source system name
7. enterprise_or_func_name - Enterprise or functional area name
8. enterprise_or_func_subgrp_name - Sub-group within the enterprise/functional area
9. region - AWS region (e.g., us-east-1, us-west-2)
10. data_construct - Data construct type
11. data_env - Environment (e.g., dev, staging, prod)
12. data_layer - Data layer (e.g., raw, curated, analytics)
13. data_leader - Name of the data leader/owner
14. data_owner_email - Email of the data owner
15. data_owner_github_uname - GitHub username of the data owner
16. pr_title - Title for the Pull Request

TOOL USAGE:
- ONLY call create_glue_database_pr when you have ALL 16 fields collected
- Do NOT call the tool if any field is missing
- After calling the tool, relay the result to the user naturally
- If the tool succeeds, congratulate the user and provide the PR link
- If the tool fails, explain the error clearly and offer to help resolve it

VALIDATION GUIDELINES:
- S3 locations should start with "s3://"
- AWS account IDs should be 12 digits
- Email addresses should contain "@"
- GitHub usernames should not contain spaces or special characters

IMPORTANT:
- Be patient and understanding if users need to look up information
- If users are unsure about a field, provide examples or explanations
- Keep responses concise but informative
- Never mention "tools", "functions", or technical implementation details to users
- Focus on helping users successfully create their PR

GENERAL CHAT:
- You can answer questions about what you do
- You can explain the Glue DB PR creation process
- If asked about other types of PRs, politely explain you currently only support Glue Database PRs
- Keep general responses helpful and concise

OUTPUT STYLE:
- Clear
- Professional
- Concise
"""

# =========================================================
# REQUIRED FIELDS (ORDER IS CRITICAL)
# =========================================================
REQUIRED_FIELDS = [
    "intake_id",
    "database_name",
    "database_s3_location",
    "database_description",
    "aws_account_id",
    "source_name",
    "enterprise_or_func_name",
    "enterprise_or_func_subgrp_name",
    "region",
    "data_construct",
    "data_env",
    "data_layer",
    "data_leader",
    "data_owner_email",
    "data_owner_github_uname",
    "pr_title",
]


def parse_comma_separated_input(text: str) -> Dict[str, str]:
    values = [v.strip() for v in text.split(",")]

    if len(values) != len(REQUIRED_FIELDS):
        raise ValueError(
            f"Expected {len(REQUIRED_FIELDS)} values but got {len(values)}.\n\n"
            "Required order:\n" + ", ".join(REQUIRED_FIELDS)
        )

    return dict(zip(REQUIRED_FIELDS, values))


# =========================================================
# MODELS
# =========================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]


class ChatResponse(BaseModel):
    response: str
    tool_used: bool = False
    pr_url: Optional[str] = None


# =========================================================
# ROUTES
# =========================================================
@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Data Platform Intake Bot",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        if not req.messages:
            return ChatResponse(
                response="Please send a message to begin.",
                tool_used=False,
            )

        last_user_message = req.messages[-1].get("content", "").strip()

        # =================================================
        # BULK COMMA-SEPARATED INPUT PATH
        # =================================================
        if "," in last_user_message:
            try:
                parsed = parse_comma_separated_input(last_user_message)

                result = create_glue_db_pr(
                    GlueDBPRInput(**parsed)
                )

                pr_url = None
                for line in result.splitlines():
                    if line.strip().startswith("🔗"):
                        pr_url = line.replace("🔗", "").strip()
                        break

                return ChatResponse(
                    response=result,
                    tool_used=True,
                    pr_url=pr_url,
                )

            except Exception as e:
                return ChatResponse(
                    response=f"❌ Invalid input\n\n{str(e)}",
                    tool_used=False,
                )

        # =================================================
        # NORMAL CHAT PATH (LLM)
        # =================================================
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(req.messages)

        llm_response = llm.invoke(messages)

        if llm_response is None or not hasattr(llm_response, "content"):
            return ChatResponse(
                response="⚠️ I could not generate a response. Please try again.",
                tool_used=False,
            )

        return ChatResponse(
            response=llm_response.content,
            tool_used=False,
        )

    except Exception as e:
        traceback.print_exc()
        return ChatResponse(
            response=f"❌ Internal server error\n\n{str(e)}",
            tool_used=False,
        )


@app.get("/health")
def health():
    return {
        "groq_key": bool(os.getenv("GROQ_API_KEY")),
        "github_token": bool(os.getenv("GITHUB_TOKEN")),
        "repo": os.getenv("REPO_NAME"),
    }
