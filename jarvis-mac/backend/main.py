import os
import subprocess
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

AUTH_TOKEN = os.getenv("ASSISTANT_AUTH_TOKEN", "local-dev-token")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_AI_MODEL = os.getenv("CLOUDFLARE_AI_MODEL", "@cf/meta/llama-3.1-8b-instruct")

app = FastAPI(title="Desktop Copilot API", version="0.3.0")
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
    provider: str = "groq"
    model: Optional[str] = None
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


def _run_osascript(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
def _run_command(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip())
    return result.stdout.strip()


def _apps() -> list[str]:
    names = []
    for root in [Path("/Applications"), Path.home() / "Applications"]:
        if root.exists():
            names.extend([p.stem for p in root.glob("*.app")])
    return sorted(set(names))


async def _call_groq(message: str, model: Optional[str]) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY missing")
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model or "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a practical desktop copilot."},
            {"role": "user", "content": message},
        ],
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=40) as client:
        res = await client.post(endpoint, json=payload, headers=headers)
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=res.text)
    data = res.json()
    return data["choices"][0]["message"]["content"]


async def _call_mistral(message: str, model: Optional[str]) -> str:
    if not MISTRAL_API_KEY:
        raise HTTPException(status_code=400, detail="MISTRAL_API_KEY missing")
    endpoint = "https://api.mistral.ai/v1/chat/completions"
    payload = {
        "model": model or "mistral-small-latest",
        "messages": [{"role": "user", "content": message}],
    }
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=40) as client:
        res = await client.post(endpoint, json=payload, headers=headers)
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=res.text)
    return res.json()["choices"][0]["message"]["content"]


async def _call_cloudflare(message: str) -> str:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        raise HTTPException(status_code=400, detail="Cloudflare credentials missing")
    endpoint = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_AI_MODEL}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=40) as client:
        res = await client.post(endpoint, headers=headers, json={"messages": [{"role": "user", "content": message}]})
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=res.text)
    data = res.json().get("result", {})
    response = data.get("response") or data.get("output_text")
    return response or str(data)


async def _save_chat(provider: str, user_message: str, assistant_reply: str) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    endpoint = f"{SUPABASE_URL}/rest/v1/chat_logs"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    payload = {"provider": provider, "user_message": user_message, "assistant_reply": assistant_reply}
    async with httpx.AsyncClient(timeout=20) as client:
        await client.post(endpoint, headers=headers, json=payload)
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
    return {"status": "ok", "service": "desktop-copilot"}
    return {"status": "ok", "version": "0.2.0"}


@app.get("/apps")
def apps(authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
    return {"apps": _apps()}


@app.post("/script/run")
def run_script(payload: ScriptRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
    return {"output": _run_osascript(payload.script)}


@app.post("/chat")
async def chat(payload: ChatRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _verify_token(authorization)
    provider = payload.provider.lower().strip()
    if provider == "groq":
        reply = await _call_groq(payload.message, payload.model)
    elif provider == "mistral":
        reply = await _call_mistral(payload.message, payload.model)
    elif provider == "cloudflare":
        reply = await _call_cloudflare(payload.message)
    else:
        raise HTTPException(status_code=400, detail="provider must be one of: groq, mistral, cloudflare")

    await _save_chat(provider, payload.message, reply)
    return {"provider": provider, "reply": reply}
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
