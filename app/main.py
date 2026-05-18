"""
AI API Observatory — Real-time AI provider health, latency, cost & validity monitoring.
FastAPI application with async background checking, Prometheus metrics,
and dynamic provider/prompt management via REST API.
"""

import asyncio
import json
import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from openai import AsyncOpenAI
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_fixed

load_dotenv()

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ai-observatory")

# ─── File Paths ───────────────────────────────────────────────────────────────
# In K8s the PVC is mounted at /app/data; locally fall back to the app directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/app/data" if os.path.isdir("/app/data") else BASE_DIR
PROVIDERS_FILE = os.path.join(DATA_DIR, "providers.json")
PROMPTS_FILE = os.path.join(DATA_DIR, "prompts.json")

# ─── In-memory State ─────────────────────────────────────────────────────────
providers: Dict[str, Dict[str, Any]] = {}
prompts: Dict[str, Dict[str, Any]] = {}
config: Dict[str, Any] = {"interval_seconds": int(os.getenv("CHECK_INTERVAL", "120"))}
simulated_failures: Dict[str, float] = {}

# ─── Prometheus Metrics ──────────────────────────────────────────────────────
api_up = Gauge("api_up", "1 if provider is reachable", ["provider", "model"])
api_response_time_seconds = Gauge(
    "api_response_time_seconds", "Response latency in seconds", ["provider", "prompt"]
)
api_tokens_used = Gauge("api_tokens_used", "Tokens consumed", ["provider", "prompt"])
api_cost_usd = Gauge("api_cost_usd", "Estimated cost in USD", ["provider", "prompt"])
api_response_valid = Gauge(
    "api_response_valid", "1 if response matches expected answer", ["provider", "prompt"]
)
api_error_total = Counter("api_error_total", "Cumulative error count categorized by root cause", ["provider", "error_type"])
api_requests_total = Counter("api_requests_total", "Cumulative request count", ["provider"])

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Persistence Helpers ─────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    """Load a JSON file; return empty dict on any error."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path: str, data: dict) -> None:
    """Atomically write dict to JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)


# ─── AI Provider Checkers ────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
async def check_groq_openai(provider: dict, prompt_text: str) -> dict:
    """Check Groq or any OpenAI-compatible provider."""
    api_key = os.getenv(provider["api_key"], "")
    client = AsyncOpenAI(api_key=api_key, base_url=provider.get("base_url"), timeout=15.0)
    try:
        response = await client.chat.completions.create(
            model=provider["model"],
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=100,
            temperature=0.1,
        )
        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        return {"text": text.strip(), "tokens": tokens}
    finally:
        await client.close()


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
async def check_gemini(provider: dict, prompt_text: str) -> dict:
    """Check Google Gemini provider (using legacy google-generativeai SDK)."""
    api_key = os.getenv(provider["api_key"], "")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(provider["model"])
    response = await model.generate_content_async(prompt_text)
    text = ""
    if response and response.text:
        text = response.text
    tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        tokens = getattr(response.usage_metadata, "total_token_count", 0)
    return {"text": text.strip(), "tokens": tokens}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
async def check_huggingface(provider: dict, prompt_text: str) -> dict:
    """Check HuggingFace Inference API."""
    api_key = os.getenv(provider["api_key"], "")
    base = provider.get("base_url") or "https://api-inference.huggingface.co/models"
    url = f"{base.rstrip('/')}/{provider['model']}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"inputs": prompt_text, "parameters": {"max_new_tokens": 100}},
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list) and len(result) > 0:
            text = result[0].get("generated_text", str(result[0]))
        else:
            text = str(result)
        tokens = len(prompt_text.split()) + len(text.split())
        return {"text": text.strip(), "tokens": tokens}


CHECKER_MAP = {
    "groq": check_groq_openai,
    "openai": check_groq_openai,
    "openrouter": check_groq_openai,
    "gemini": check_gemini,
    "huggingface": check_huggingface,
}

# ─── Single Provider+Prompt Check ────────────────────────────────────────────

async def check_single(
    provider_id: str, provider: dict, prompt_id: str, prompt: dict
) -> None:
    """Check one provider against one prompt. Updates metrics + state."""
    name = provider["name"]
    model = provider["model"]
    prompt_text = prompt["text"]
    expected = prompt.get("expected_answer", "")
    prompt_label = prompt_text[:50]

    api_requests_total.labels(provider=name).inc()

    # Handle simulated failures
    if provider_id in simulated_failures:
        if time.time() < simulated_failures[provider_id]:
            api_up.labels(provider=name, model=model).set(0)
            api_error_total.labels(provider=name, error_type="simulated").inc()
            api_response_valid.labels(provider=name, prompt=prompt_label).set(0)
            logger.warning("[SIMULATED FAILURE] %s", name)
            return
        else:
            del simulated_failures[provider_id]

    checker = CHECKER_MAP.get(provider.get("provider_type", "").lower())
    if not checker:
        logger.error("Unknown provider_type: %s", provider.get("provider_type"))
        api_up.labels(provider=name, model=model).set(0)
        api_error_total.labels(provider=name, error_type="unknown_type").inc()
        return

    start = time.time()
    try:
        result = await checker(provider, prompt_text)
        elapsed = time.time() - start
        tokens = result.get("tokens", 0)
        response_text = result.get("text", "")
        cost = (tokens / 1000.0) * provider.get("cost_per_1k_tokens", 0.0)

        if expected:
            valid = 1 if expected.strip().lower() in response_text.strip().lower() else 0
        else:
            valid = 1

        api_up.labels(provider=name, model=model).set(1)
        api_response_time_seconds.labels(provider=name, prompt=prompt_label).set(elapsed)
        api_tokens_used.labels(provider=name, prompt=prompt_label).set(tokens)
        api_cost_usd.labels(provider=name, prompt=prompt_label).set(cost)
        api_response_valid.labels(provider=name, prompt=prompt_label).set(valid)

        provider["status"] = "up"
        provider["last_checked"] = datetime.now(timezone.utc).isoformat()
        provider["last_response_time"] = round(elapsed, 3)

        logger.info("OK  %s | %.2fs | %d tok | valid=%d", name, elapsed, tokens, valid)

    except Exception as exc:
        elapsed = time.time() - start
        api_up.labels(provider=name, model=model).set(0)
        
        # Determine error type dynamically
        error_type = "generic_internal"
        exc_str = str(exc).lower()
        if "timeout" in exc_str or "timed out" in exc_str:
            error_type = "timeout"
        elif "rate limit" in exc_str or "429" in exc_str or "quota" in exc_str:
            error_type = "rate_limit_429"
        elif "401" in exc_str or "unauthorized" in exc_str or "credentials" in exc_str:
            error_type = "auth_401"
        elif "402" in exc_str or "payment" in exc_str or "limit exceeded" in exc_str:
            error_type = "payment_required_402"
        elif "404" in exc_str or "not found" in exc_str:
            error_type = "not_found_404"

        api_error_total.labels(provider=name, error_type=error_type).inc()
        api_response_time_seconds.labels(provider=name, prompt=prompt_label).set(elapsed)
        api_response_valid.labels(provider=name, prompt=prompt_label).set(0)

        provider["status"] = "down"
        provider["last_checked"] = datetime.now(timezone.utc).isoformat()

        logger.error("ERR %s | %s", name, exc)


# ─── Background Checker Loop ─────────────────────────────────────────────────

async def checker_loop() -> None:
    """Runs forever — checks all providers × all prompts each cycle."""
    await asyncio.sleep(5)
    while True:
        try:
            if providers and prompts:
                tasks = [
                    check_single(pid, prov, qid, qdata)
                    for pid, prov in list(providers.items())
                    for qid, qdata in list(prompts.items())
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                logger.info("Waiting — no providers or prompts configured yet.")
        except Exception as exc:
            logger.error("Checker loop error (continuing): %s", exc)
        await asyncio.sleep(config.get("interval_seconds", 120))


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global providers, prompts
    providers = load_json(PROVIDERS_FILE)
    prompts = load_json(PROMPTS_FILE)
    logger.info("Loaded %d providers, %d prompts", len(providers), len(prompts))
    task = asyncio.create_task(checker_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI API Observatory",
    description="Real-time AI provider health, latency, cost & validity monitoring",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Max 10 requests/minute."},
    )


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    name: str
    api_key: str
    model: str
    provider_type: str
    base_url: Optional[str] = None
    cost_per_1k_tokens: float = 0.0


class PromptCreate(BaseModel):
    text: str
    expected_answer: str = ""


class ConfigUpdate(BaseModel):
    interval_seconds: int = Field(ge=10, le=3600)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "AI API Observatory",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers_count": len(providers),
        "prompts_count": len(prompts),
    }


@app.get("/providers")
async def list_providers():
    return {"providers": providers, "count": len(providers)}


@app.post("/providers")
@limiter.limit("10/minute")
async def add_provider(provider: ProviderCreate, request: Request):
    pid = str(uuid.uuid4())[:8]
    providers[pid] = {
        **provider.model_dump(),
        "status": "unknown",
        "last_checked": None,
        "last_response_time": None,
    }
    save_json(PROVIDERS_FILE, providers)
    logger.info("Added provider %s (%s)", provider.name, pid)
    return {"id": pid, "provider": providers[pid]}


@app.delete("/providers/{provider_id}")
async def remove_provider(provider_id: str):
    if provider_id not in providers:
        raise HTTPException(status_code=404, detail="Provider not found")
    removed = providers.pop(provider_id)
    simulated_failures.pop(provider_id, None)
    save_json(PROVIDERS_FILE, providers)
    logger.info("Removed provider %s", removed["name"])
    return {"removed": removed}


@app.get("/prompts")
async def list_prompts():
    return {"prompts": prompts, "count": len(prompts)}


@app.post("/prompts")
@limiter.limit("10/minute")
async def add_prompt(prompt: PromptCreate, request: Request):
    qid = str(uuid.uuid4())[:8]
    prompts[qid] = prompt.model_dump()
    save_json(PROMPTS_FILE, prompts)
    logger.info("Added prompt %s", qid)
    return {"id": qid, "prompt": prompts[qid]}


@app.delete("/prompts/{prompt_id}")
async def remove_prompt(prompt_id: str):
    if prompt_id not in prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")
    removed = prompts.pop(prompt_id)
    save_json(PROMPTS_FILE, prompts)
    logger.info("Removed prompt %s", prompt_id)
    return {"removed": removed}


@app.get("/config")
async def get_config():
    return config


@app.put("/config")
async def update_config(update: ConfigUpdate):
    config["interval_seconds"] = update.interval_seconds
    logger.info("Config updated: interval_seconds=%d", update.interval_seconds)
    return config


@app.post("/simulate/failure/{provider_id}")
@limiter.limit("10/minute")
async def simulate_failure(provider_id: str, request: Request):
    if provider_id not in providers:
        raise HTTPException(status_code=404, detail="Provider not found")
    expiry = time.time() + 180
    simulated_failures[provider_id] = expiry
    logger.info("Simulated failure for %s (3 min)", providers[provider_id]["name"])
    return {
        "message": f"Simulated failure for {providers[provider_id]['name']} — 3 minutes",
        "expires_at": datetime.fromtimestamp(expiry, tz=timezone.utc).isoformat(),
    }


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
