"""Tenri Web backend — FastAPI app (stateless, keyless, BYOK).

Run (from repo root):
    uvicorn backend.main:app --reload --port 8000

Endpoints:
    GET  /health   -> readiness + KB/model info
    POST /route    -> classify a turn; for ANSWER, returns the grounded prompt
                      the browser sends to Groq with the user's own key
    POST /verify   -> grounding check on a generated answer
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.brain import TenriBrain
from backend.schemas import (
    HealthResponse,
    RouteRequest,
    RouteResponse,
    VerifyRequest,
    VerifyResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TenriWeb")

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_brain()  # load KB once at boot so the first request is fast
    yield


app = FastAPI(title="Tenri Web Backend", version="0.1.0", lifespan=lifespan)

# CORS: only the frontend origin(s). Comma-separated FRONTEND_ORIGINS env var;
# defaults to local Next.js dev. The browser sends NO secrets to us (BYOK), but
# we still restrict origins to our own frontend.
_origins = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_brain: TenriBrain | None = None


def get_brain() -> TenriBrain:
    global _brain
    if _brain is None:
        _brain = TenriBrain()
    return _brain


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    b = get_brain()
    return HealthResponse(
        status="ok",
        slides=b.slide_count,
        chunks=b.chunk_count,
        live_model=b.live_model,
    )


@app.post("/route", response_model=RouteResponse)
def route(req: RouteRequest) -> RouteResponse:
    return RouteResponse(**get_brain().route(req))


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest) -> VerifyResponse:
    return VerifyResponse(**get_brain().verify(req.response, req.context_str))
