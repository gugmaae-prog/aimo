# Jarvis for macOS (Full-Stack)

Upgraded local assistant with secure local token auth and direct Mac controls.

## Features
- Conversational `/chat` endpoint with rule-based commands (`open Safari`, `quit Music`, `run script: ...`) and optional OpenAI fallback.
- App management endpoints: list installed apps, launch, and quit.
- AppleScript runner and controlled shell runner (`/shell/run`) with allow-listed commands.
- Browser frontend with chat, app controls, speech-to-text input, and text-to-speech output.

## Backend setup
# Jarvis for macOS (Full-Stack Starter)

This project gives you a **Jarvis-like local assistant** for your Mac with:
- Backend API to list, launch, and quit installed apps.
- AppleScript execution endpoint for deeper local automation.
- Chat endpoint that can use OpenAI when `OPENAI_API_KEY` is set.
- Frontend web UI for chat + app controls.

## Architecture
- `backend/main.py` — FastAPI service for app control and chat.
- `frontend/index.html` — lightweight dashboard UI.

## Run backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export JARVIS_AUTH_TOKEN='replace-me'
export OPENAI_API_KEY='optional'
uvicorn main:app --reload --port 8000
```

## Frontend
Open `frontend/index.html` and set:
- Backend URL (default `http://localhost:8000`)
- Auth Token (must match `JARVIS_AUTH_TOKEN`)

## API security notes
- All sensitive endpoints require `Authorization: Bearer <token>`.
- `/shell/run` only allows these commands: `open`, `say`, `osascript`, `pmset`, `afplay`.
- Keep this app local-only unless you add proper auth, TLS, and auditing.
export OPENAI_API_KEY=your_key_here   # optional
uvicorn main:app --reload --port 8000
```

## Run frontend
Open `frontend/index.html` in your browser.

## Notes for macOS permissions
For app control and scripting to work, macOS may prompt for permissions:
- Terminal / Python needs **Automation** and sometimes **Accessibility** access.
- You may need to allow control of specific apps in System Settings.

## Safety
The `/script/run` endpoint executes AppleScript as-is. Protect it behind auth if exposed beyond localhost.
