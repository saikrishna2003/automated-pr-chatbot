import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant",
    temperature=0.3
)

REQUIRED_FIELDS = [
    "intake_id",
    "database_name",
    "database_s3_location",
    "database_description",
    "aws_account_id",
    "region",
    "data_construct",
    "data_env",
    "data_layer",
    "source_name",
    "enterprise_or_func_name",
    "enterprise_or_func_subgrp_name",
    "data_owner_email",
    "data_owner_github_uname",
    "data_leader",
]

FIELD_QUESTIONS = {
    "intake_id": "What’s the intake ID?",
    "database_name": "What should we name the Glue database?",
    "database_s3_location": "Where should the data live in S3?",
    "database_description": "Short description of this database?",
    "aws_account_id": "Which AWS account ID?",
    "region": "Which AWS region?",
    "data_construct": "Is this Source or Consumer?",
    "data_env": "Which environment? (dev / qa / prd)",
    "data_layer": "Which data layer?",
    "source_name": "What’s the source system name?",
    "enterprise_or_func_name": "Enterprise or functional group name?",
    "enterprise_or_func_subgrp_name": "Sub-group name?",
    "data_owner_email": "Data owner email?",
    "data_owner_github_uname": "Data owner GitHub username?",
    "data_leader": "Who is the data leader?",
}

state = {
    "active": False,
    "index": 0,
    "data": {},
    "awaiting_pr_title": False,
}

def is_glue_intent(text: str) -> bool:
    t = text.replace(" ", "")
    return any(x in t for x in ["glue", "gluedb", "gludb", "gluedatabase"])

def ask_groq(user_input: str):
    text = user_input.lower().strip()

    # ---------- CAPABILITIES ----------
    if "pr" in text and "support" in text:
        return {
            "type": "message",
            "content": (
                "I can help with:\n\n"
                "✅ Glue Database PRs\n"
                "🚧 IAM PRs (coming soon)\n"
                "🚧 Resource Policy PRs (coming soon)\n\n"
                "Say **create glue db** to begin 🚀"
            )
        }

    # ---------- START FLOW ----------
    if is_glue_intent(text) and not state["active"]:
        state["active"] = True
        state["index"] = 0
        state["data"] = {}
        state["awaiting_pr_title"] = False

        first = REQUIRED_FIELDS[0]
        return {
            "type": "message",
            "content": f"Great 👍 Let’s get started.\n\n{FIELD_QUESTIONS[first]}"
        }

    # ---------- COLLECT FIELDS ----------
    if state["active"] and not state["awaiting_pr_title"]:
        field = REQUIRED_FIELDS[state["index"]]
        state["data"][field] = user_input.strip()
        state["index"] += 1

        if state["index"] < len(REQUIRED_FIELDS):
            next_field = REQUIRED_FIELDS[state["index"]]
            return {
                "type": "message",
                "content": FIELD_QUESTIONS[next_field]
            }

        state["awaiting_pr_title"] = True
        return {
            "type": "message",
            "content": (
                "Nice 👍 I’ve captured all required details.\n\n"
                "What should be the **Pull Request title**?"
            )
        }

    # ---------- PR TITLE ----------
    if state["awaiting_pr_title"]:
        pr_title = user_input.strip()

        payload = state["data"]

        # RESET STATE
        state["active"] = False
        state["index"] = 0
        state["data"] = {}
        state["awaiting_pr_title"] = False

        return {
            "type": "action",
            "action": "create_pr",
            "data": payload,
            "pr_title": pr_title
        }

    # ---------- FALLBACK ----------
    return {
        "type": "message",
        "content": "🙂 You can say **create glue db** to start."
    }
