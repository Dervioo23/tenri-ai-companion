# Tenri Web Frontend (Phase 1 — MVP push-to-talk, BYOK)

Next.js (App Router, TypeScript) frontend for Tenri. The user enters their **own**
Groq + ElevenLabs API keys (BYOK). Keys live only in the browser (sessionStorage)
and go **straight to the providers** — never to our backend.

## Flow (one turn)
`Tahan untuk bicara` → record → **Groq Whisper** (browser) → transcript →
backend **`/route`** (decision + grounded prompt) → **Groq chat** (browser) →
backend **`/verify`** (grounding) → **ElevenLabs TTS** (browser) → play.

Hybrid addressee model works: say **"Tenri"** to open the window, then ask or
debate freely; say **"terima kasih"** to close.

## Run locally
```bash
# 1. Start the backend (repo root):
uvicorn backend.main:app --port 8000

# 2. Frontend:
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm install
npm run dev                        # http://localhost:3000
```
Open the page, paste your Groq + ElevenLabs keys, click **Test & Simpan**
(this also verifies the R1 CORS gate), then hold the button and talk.

## Deploy
- **Frontend → Vercel**: import the `frontend/` directory; set `NEXT_PUBLIC_BACKEND_URL`
  to the deployed backend URL.
- **Backend → Render/Railway**: see `../backend/README.md`. Set `FRONTEND_ORIGINS`
  to the Vercel domain.

## R1 — CORS gate
`Test & Simpan` calls Groq `/models` and ElevenLabs `/voices` directly from the
browser. If those succeed, **BYOK Cara A works** (keys never touch our server).
If they fail with a CORS/network error, providers block direct browser calls and
we add a thin stateless proxy in the backend (see the implementation plan, R1).

## Mic + HTTPS
`getUserMedia` requires a secure context: `localhost` (dev) or HTTPS (Vercel is
HTTPS by default). Grant the microphone permission when prompted.
