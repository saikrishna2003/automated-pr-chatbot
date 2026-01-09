from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import truststore
import os

# Use OS trust store globally (Windows/macOS/Linux)
truststore.inject_into_ssl()

# Set API key via env var (recommended)
os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY"

llm = ChatGoogleGenerativeAI(
    model="gemini-1.0-pro",
    temperature=0,
)

SYSTEM_PROMPT = """
You are Data Platform Intake Bot.

Your job is to:
1. Collect required metadata for creating a data intake configuration.
2. Ask one question at a time.
3. Maintain a friendly, professional DevOps assistant tone.
4. Never generate YAML or code unless explicitly asked.
5. If a value is already provided, do not ask again.
6. Once all fields are collected, respond with:
   'All required details are collected. Ready to generate config.'

Required fields:
- intake_id
- database_name
- database_s3_location
- database_description
- aws_account_id
- region
- data_construct
- data_env
- data_layer
- source_name
- enterprise_or_func_name
- enterprise_or_func_subgrp_name
"""

def ask_gemini(user_input: str) -> str:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_input),
    ]
    response = llm.invoke(messages)
    return response.content


