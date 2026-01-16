# This file can be deleted now since all LLM logic is in api.py
# Or keep it as a utility if you want to reuse the LLM setup elsewhere

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def get_llm():
    """Returns configured LLM instance"""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
    )
