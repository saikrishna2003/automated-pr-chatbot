from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from app.chatbot import ask_groq
from app.yaml_generator import generate_yaml
from app.git_ops import create_branch_and_commit, create_pull_request

app = FastAPI(title="Data Platform Intake Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        result = ask_groq(req.message)

        # ---------- NORMAL CHAT MESSAGE ----------
        if result["type"] == "message":
            return {"response": result["content"]}

        # ---------- CREATE PR ACTION ----------
        if result["type"] == "action" and result["action"] == "create_pr":
            data = result["data"]
            pr_title = result["pr_title"]

            yaml_content = generate_yaml(data)

            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            yaml_dir = os.path.join(repo_root, "intake_configs")
            os.makedirs(yaml_dir, exist_ok=True)

            yaml_path = os.path.join(
                yaml_dir, f"{data['database_name']}.yaml"
            )

            branch_name = f"intake/{data['intake_id']}"

            create_branch_and_commit(
                repo_path=repo_root,
                branch_name=branch_name,
                yaml_file_path=yaml_path,
                yaml_content=yaml_content,
            )

            pr = create_pull_request(
                github_token=os.getenv("GITHUB_TOKEN"),
                repo_name=os.getenv("REPO_NAME"),
                branch_name=branch_name,
                base_branch=os.getenv("BASE_BRANCH", "main"),
                pr_title=pr_title,
            )

            return {
                "response": (
                    "🚀 **Pull Request Created Successfully!**\n\n"
                    f"🔗 {pr['html_url']}"
                )
            }

        return {"response": "⚠️ Unexpected response from chatbot."}

    except Exception as e:
        return {"response": f"❌ Backend error: {str(e)}"}
