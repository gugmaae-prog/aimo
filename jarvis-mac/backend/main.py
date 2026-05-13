import os
import shlex
import subprocess
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

AUTH_TOKEN = os.getenv("JARVIS_AUTH_TOKEN", "local-dev-token")

app = FastAPI(title="Jarvis Mac Assistant", version="0.2.0")
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


class ShellRequest(BaseModel):
    command: str


def _verify_token(authorization: Optional[str]) -> None:
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _run_command(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip())
    return result.stdout.strip()


def _applications() -> List[str]:
    apps = []
    for root in [Path("/Applications"), Path.home() / "Applications"]:
        if root.exists():
            apps.extend([p.stem for p in root.glob("*.app")])
    return sorted(set(apps))


def _rule_based_action(text: str) -> dict:
    t = text.lower().strip()
    if t.startswith("open "):
        return {"type": "launch_app", "app_name": text[5:].strip()}
    if t.startswith("launch "):
        return {"type": "launch_app", "app_name": text[7:].strip()}
    if t.startswith("quit "):
        return {"type": "quit_app", "app_name": text[5:].strip()}
    if t.startswith("run script:"):
        return {"type": "run_script", "script": text.split(":", 1)[1].strip()}
    return {"type": "none"}
    apps_dir = Path("/Applications")
    if not apps_dir.exists():
        return []
    return sorted([p.stem for p in apps_dir.glob("*.app")])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.2.0"}


@app.get("/apps")
def apps(authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
    return {"status": "ok"}


@app.get("/apps")
def apps() -> dict:
    return {"apps": _applications()}


@app.post("/apps/launch")
def launch_app(payload: ActionRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
def launch_app(payload: ActionRequest) -> dict:
    _run_command(["open", "-a", payload.app_name])
    return {"launched": payload.app_name}


@app.post("/apps/quit")
def quit_app(payload: ActionRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
def quit_app(payload: ActionRequest) -> dict:
    script = f'tell application "{payload.app_name}" to quit'
    _run_command(["osascript", "-e", script])
    return {"quit": payload.app_name}


@app.post("/script/run")
def run_applescript(payload: ScriptRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
def run_applescript(payload: ScriptRequest) -> dict:
    output = _run_command(["osascript", "-e", payload.script])
    return {"output": output}


@app.post("/shell/run")
def run_shell(payload: ShellRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
    cmd = shlex.split(payload.command)
    if cmd[:1] not in [["open"], ["say"], ["osascript"], ["pmset"], ["afplay"]]:
        raise HTTPException(status_code=400, detail="Command not allowed")
    output = _run_command(cmd)
    return {"output": output}


@app.post("/chat")
def chat(payload: ChatRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
    action = _rule_based_action(payload.message)

    if action["type"] == "launch_app":
        _run_command(["open", "-a", action["app_name"]])
        return {"reply": f"Launching {action['app_name']}", "action": action}
    if action["type"] == "quit_app":
        _run_command(["osascript", "-e", f'tell application "{action["app_name"]}" to quit'])
        return {"reply": f"Quitting {action['app_name']}", "action": action}
    if action["type"] == "run_script":
        out = _run_command(["osascript", "-e", action["script"]])
        return {"reply": f"Script executed. {out}", "action": action}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return {"reply": "Try commands: 'open Safari', 'quit Music', or 'run script: say hello'.", "action": action}

    client = OpenAI(api_key=api_key)
    resp = client.responses.create(
        model=payload.model,
        input=[
            {"role": "system", "content": "You are Jarvis on macOS. Keep replies short and practical."},
            {"role": "user", "content": payload.message},
        ],
    )
    return {"reply": resp.output_text, "action": action}
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
