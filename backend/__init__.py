"""Tenri Web backend — stateless FastAPI 'brain' (BYOK).

Reuses the existing terminal app's brain modules (intent, retrieval, grounding,
prompt building) under ``app.*``. No API keys and no audio live here: LLM/STT/TTS
are called from the browser with the user's own keys (BYOK Cara A).
"""
