"""FastAPI backend for the Policy-Aware Multi-Agent RAG Claim Decision Engine.

Endpoints:
    POST /analyze   -- analyze one claim case, returns DecisionResponse
    GET  /health     -- readiness check
    GET  /policy/chunks/{chunk_id}  -- inspect a cited policy chunk (reviewer UI helper)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Explicit path (repo_root/.env), independent of the working directory
# uvicorn/streamlit happens to be launched from -- must run before anything
# below reads GROQ_API_KEY / ANTHROPIC_API_KEY / etc.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("claim_engine")

if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
    logger.info(".env loaded from %s", _ENV_PATH)
else:
    # Common Windows footgun: Notepad/Explorer hide known extensions, so a
    # file saved as ".env" can silently become ".env.txt". Check for it and
    # load it anyway (with a loud warning) instead of failing silently.
    _fallback = _ENV_PATH.parent / ".env.txt"
    if _fallback.exists():
        load_dotenv(dotenv_path=_fallback)
        logger.warning(
            "No .env found at %s, but found %s instead -- loaded it anyway. "
            "This is almost always Windows hiding the real file extension. "
            "Rename it to '.env' (no .txt) to fix this properly: "
            "Rename-Item '.env.txt' '.env'",
            _ENV_PATH, _fallback,
        )
    else:
        logger.warning(
            "No .env file found at %s (nor %s). Running with LLM_PROVIDER=none "
            "unless GROQ_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY are set as real "
            "OS environment variables. Create the file with: "
            "Copy-Item .env.example .env",
            _ENV_PATH, _fallback,
        )

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .models import ClaimCase, DecisionResponse
from .orchestrator import ClaimEngine

_engine: ClaimEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    logger.info("Loading policy index and building retrievers...")
    _engine = ClaimEngine()
    from .llm import LLMClient
    provider = LLMClient().provider
    logger.info("Ready. LLM provider resolved to: %s", provider)
    yield


app = FastAPI(
    title="Policy-Aware Multi-Agent RAG Claim Decision Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "engine_ready": _engine is not None}


@app.post("/analyze", response_model=DecisionResponse)
def analyze(payload: dict):
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    try:
        case = ClaimCase.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    try:
        return _engine.analyze(case)
    except Exception as e:  # graceful handling of malformed/unsupported input
        logger.exception("Analysis failed for case %s", payload.get("case_id"))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.get("/llm-status")
def llm_status(test: bool = False):
    """Diagnostic endpoint to check whether an LLM is configured and
    reachable, independent of running a full claim analysis.

    - GET /llm-status          -> reports which provider/model is configured
    - GET /llm-status?test=true -> also makes one real, tiny completion call
                                     and reports whether it actually succeeded
    """
    from .llm import LLMClient

    client = LLMClient()
    result = {
        "provider": client.provider,
        "available": client.available,
        "env_file_found": _ENV_PATH.exists(),
        "env_file_path": str(_ENV_PATH),
        "env_txt_fallback_found": (_ENV_PATH.parent / ".env.txt").exists(),
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
    }
    if test:
        text = client.complete("Reply with exactly: OK", "Reply with exactly: OK", max_tokens=50)
        result["test_call"] = client.last_call_info
        result["test_call"]["response_text"] = text
    return result


@app.get("/policy/chunks/{chunk_id}")
def get_chunk(chunk_id: str):
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    for c in _engine.policy_params.chunks:
        if c["chunk_id"] == chunk_id:
            return c
    raise HTTPException(status_code=404, detail="chunk not found")
