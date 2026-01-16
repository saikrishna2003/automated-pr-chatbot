"""
Data Platform Intake Bot - Main API
Fully LLM-driven intake system for creating automated PRs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import traceback
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.tools import StructuredTool
from app.tools.glue_pr_tool import create_glue_db_pr, GlueDBPRInput

# Load environment variables
load_dotenv()

# =========================================================
# FastAPI app initialization
# =========================================================
app = FastAPI(
    title="Data Platform Intake Bot",
    description="LLM-driven chatbot for automated PR creation",
    version="2.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# LLM Configuration with Tool Binding
# =========================================================
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant",
    temperature=0.1,
)

# Define the Glue DB PR creation tool
glue_pr_tool = StructuredTool.from_function(
    func=create_glue_db_pr,
    name="create_glue_database_pr",
    description=(
        "Create a GitHub Pull Request for a Glue Database intake. "
        "Use this ONLY when you have collected ALL 16 required fields: "
        "intake_id, database_name, database_s3_location, database_description, "
        "aws_account_id, source_name, enterprise_or_func_name, "
        "enterprise_or_func_subgrp_name, region, data_construct, data_env, "
        "data_layer, data_leader, data_owner_email, data_owner_github_uname, pr_title"
    ),
    args_schema=GlueDBPRInput,
)

# Bind tools to LLM
llm_with_tools = llm.bind_tools([glue_pr_tool])

# =========================================================
# System Prompt
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
# Request/Response Models
# =========================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]

class ChatResponse(BaseModel):
    response: str
    tool_used: bool = False
    pr_url: Optional[str] = None

# =========================================================
# API Endpoints
# =========================================================
@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Data Platform Intake Bot",
        "version": "2.0.0",
        "llm_model": "llama-3.1-8b-instant"
    }

@app.get("/health")
def health_check():
    """Detailed health check"""
    try:
        # Check if environment variables are set
        groq_key = os.getenv("GROQ_API_KEY")
        github_token = os.getenv("GITHUB_TOKEN")
        repo_name = os.getenv("REPO_NAME")

        return {
            "status": "healthy",
            "groq_configured": bool(groq_key),
            "github_configured": bool(github_token),
            "repo_configured": bool(repo_name),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Main chat endpoint - handles all user interactions

    The LLM intelligently:
    - Understands user intent
    - Collects required information
    - Calls tools when appropriate
    - Provides helpful responses
    """
    try:
        # Build messages with system prompt
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + req.messages

        # Invoke LLM with tools
        response = llm_with_tools.invoke(messages)

        # Check if LLM wants to use a tool
        if response.tool_calls:
            tool_call = response.tool_calls[0]

            # Execute the tool
            try:
                result = create_glue_db_pr(GlueDBPRInput(**tool_call["args"]))

                # Extract PR URL if successful
                pr_url = None
                if "🔗" in result:
                    # Extract URL from result message
                    lines = result.split("\n")
                    for line in lines:
                        if "🔗" in line:
                            pr_url = line.replace("🔗", "").strip()
                            break

                return ChatResponse(
                    response=result,
                    tool_used=True,
                    pr_url=pr_url
                )
            except Exception as e:
                error_trace = traceback.format_exc()
                print(f"Tool execution error: {error_trace}")

                return ChatResponse(
                    response=f"❌ Error creating PR: {str(e)}\n\nPlease verify all information and try again.",
                    tool_used=True
                )

        # Regular conversation response (no tool call)
        return ChatResponse(
            response=response.content,
            tool_used=False
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Chat endpoint error: {error_trace}")

        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/reset")
def reset_conversation():
    """
    Reset conversation state (if needed in future for session management)
    Currently returns success as LLM is stateless
    """
    return {
        "status": "success",
        "message": "Conversation reset (LLM is stateless)"
    }

# =========================================================
# Development & Debug Endpoints
# =========================================================
@app.get("/tools")
def list_tools():
    """List available tools for debugging"""
    return {
        "tools": [
            {
                "name": glue_pr_tool.name,
                "description": glue_pr_tool.description,
                "parameters": list(GlueDBPRInput.model_fields.keys())
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )