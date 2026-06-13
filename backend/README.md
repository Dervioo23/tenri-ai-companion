# Tenri Web Backend (Phase 0)

Stateless **FastAPI "brain"** for the web version of Tenri. It reuses the existing
terminal app's brain modules (`app/services/*`, `app/core/*`) for intent routing,
retrieval, grounding, and prompt building.

**It holds no API keys and touches no audio.** STT (Groq Whisper), the LLM (Groq),
and TTS (ElevenLabs) are called **from the browser with the user's own keys**
(BYOK Cara A). The backend only turns a transcript into a routing decision and,
for answers, a grounded prompt for the browser to run.

## Run (from repo root)

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

The repo root must be on `PYTHONPATH` (running from the repo root handles this) so
`import app.*` resolves.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Readiness + slide/chunk counts + suggested model |
| POST | `/route` | Classify a turn. For `action: "answer"`, returns `messages` + `llm` params for the browser to send to Groq, plus `context_str` for `/verify`. |
| POST | `/verify` | Grounding check on a generated answer. |

### `/route` request
```json
{
  "transcript": "jelaskan slide ini tenri",
  "slide_index": 0,
  "history": [{"role": "user", "content": "..."}],
  "in_conversation": false,
  "quiet_mode": false
}
```

### `/route` response actions
`answer` · `navigate` · `slide_info` · `slide_list` · `wake_ack` · `close` · `monitor` · `ignore`

The response also carries conversation-state hints the client applies locally:
`extend_window`, `clear_quiet`, `set_quiet`, `clear_window`.

## Config

- `FRONTEND_ORIGINS` — comma-separated allowed CORS origins (default `http://localhost:3000`).
- Brain parameters are read from the repo `.env` via `app.config.Config` (model
  names, response caps). **No provider API keys are used here.**

## Notes / next

- `backend/constants.py` mirrors conversation vocab from
  `app/core/interaction_loop.py` (that module is audio-coupled and can't be
  imported here). A later refactor should extract a shared audio-free vocab module.
- Phase 1 builds the Next.js frontend (push-to-talk + BYOK) against these endpoints.
