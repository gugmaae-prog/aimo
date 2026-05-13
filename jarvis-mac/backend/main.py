import os
import subprocess
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

app = FastAPI(title="Jarvis Mac Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "gpt-4.1-mini"


class ActionRequest(BaseModel):
    app_name: str


class ScriptRequest(BaseModel):
    script: str


def _run_command(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip())
    return result.stdout.strip()


def _applications() -> List[str]:
    apps_dir = Path("/Applications")
    if not apps_dir.exists():
        return []
    return sorted([p.stem for p in apps_dir.glob("*.app")])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/apps")
def apps() -> dict:
    return {"apps": _applications()}


@app.post("/apps/launch")
def launch_app(payload: ActionRequest) -> dict:
    _run_command(["open", "-a", payload.app_name])
    return {"launched": payload.app_name}


@app.post("/apps/quit")
def quit_app(payload: ActionRequest) -> dict:
    script = f'tell application "{payload.app_name}" to quit'
    _run_command(["osascript", "-e", script])
    return {"quit": payload.app_name}


@app.post("/script/run")
def run_applescript(payload: ScriptRequest) -> dict:
    output = _run_command(["osascript", "-e", payload.script])
    return {"output": output}


@app.post("/chat")
def chat(payload: ChatRequest) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "reply": "OPENAI_API_KEY is not set. I can still launch and control local apps via API endpoints.",
            "actions": [],
        }

    if OpenAI is None:
        raise HTTPException(status_code=500, detail="openai package is not available")

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are a local macOS assistant. Respond briefly and include optional action hints "
        "as JSON under key 'actions' with elements like "
        "{'type':'launch_app','app_name':'Safari'} when appropriate."
    )

    resp = client.responses.create(
        model=payload.model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload.message},
        ],
    )

    return {"reply": resp.output_text, "actions": []}
