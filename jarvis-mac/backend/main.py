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


class ScriptRequest(BaseModel):
    script: str


def _verify_token(authorization: Optional[str]) -> None:
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _run_osascript(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "desktop-copilot"}


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
