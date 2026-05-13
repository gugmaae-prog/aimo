# Desktop Copilot for macOS

You said you do **not** want Jarvis specifically — this project is now a **similar local desktop copilot** that integrates:
- **Supabase** (chat log persistence)
- **Cloudflare AI**
- **Groq**
- **Mistral**

## What it does
- Local FastAPI service for:
  - `POST /chat` (choose provider: `groq`, `mistral`, `cloudflare`)
  - `GET /apps` (list installed apps)
  - `POST /script/run` (run AppleScript)
- Browser frontend to call all endpoints.
- Token-protected API via `ASSISTANT_AUTH_TOKEN`.
- Optional Supabase write to `chat_logs` table after each chat.

## Environment variables
Create `.env` in `backend/`:

```env
ASSISTANT_AUTH_TOKEN=replace-me

# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_KEY

# Groq
GROQ_API_KEY=YOUR_GROQ_KEY

# Mistral
MISTRAL_API_KEY=YOUR_MISTRAL_KEY

# Cloudflare AI
CLOUDFLARE_ACCOUNT_ID=YOUR_ACCOUNT_ID
CLOUDFLARE_API_TOKEN=YOUR_API_TOKEN
CLOUDFLARE_AI_MODEL=@cf/meta/llama-3.1-8b-instruct
```

## Run
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open `frontend/index.html` in your browser.

## Supabase table example
```sql
create table if not exists public.chat_logs (
  id bigserial primary key,
  provider text not null,
  user_message text not null,
  assistant_reply text not null,
  created_at timestamptz default now()
);
```

## Security notes
- Keep backend local unless you add proper auth, TLS, and rate limits.
- `/script/run` executes AppleScript directly; do not expose publicly.
