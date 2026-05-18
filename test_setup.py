import httpx

base = "http://localhost:8000"

# 1. Add OpenRouter provider
r = httpx.post(f"{base}/providers", json={
    "name": "OpenRouter",
    "api_key": "OPENROUTER_API_KEY",
    "model": "meta-llama/llama-3.3-70b-instruct:free",
    "provider_type": "openrouter",
    "base_url": "https://openrouter.ai/api/v1",
    "cost_per_1k_tokens": 0.0
})
groq_id = r.json()["id"]
print(f"1. Added OpenRouter: id={groq_id}")

# 2. Add Gemini provider
r = httpx.post(f"{base}/providers", json={
    "name": "Gemini",
    "api_key": "GEMINI_API_KEY",
    "model": "gemini-2.5-flash",
    "provider_type": "gemini",
    "cost_per_1k_tokens": 0.0002
})
gemini_id = r.json()["id"]
print(f"2. Added Gemini: id={gemini_id}")

# 3. Add HuggingFace provider
r = httpx.post(f"{base}/providers", json={
    "name": "HuggingFace",
    "api_key": "HF_API_KEY",
    "model": "facebook/bart-large-cnn",
    "provider_type": "huggingface",
    "base_url": "https://router.huggingface.co/hf-inference/models",
    "cost_per_1k_tokens": 0.0
})
hf_id = r.json()["id"]
print(f"3. Added HuggingFace: id={hf_id}")

# 4. Add a prompt
r = httpx.post(f"{base}/prompts", json={
    "text": "What is 2+2? Answer with just the number.",
    "expected_answer": "4"
})
prompt_id = r.json()["id"]
print(f"4. Added prompt: id={prompt_id}")

# 5. Check providers list
r = httpx.get(f"{base}/providers")
count = r.json()["count"]
print(f"5. Providers count: {count}")

# 6. Check prompts list
r = httpx.get(f"{base}/prompts")
count = r.json()["count"]
print(f"6. Prompts count: {count}")

# 7. Health check
r = httpx.get(f"{base}/")
status = r.json()["status"]
print(f"7. Health: {status}")

# 8. Config
r = httpx.get(f"{base}/config")
interval = r.json()["interval_seconds"]
print(f"8. Config: interval={interval}s")

# 9. Metrics
r = httpx.get(f"{base}/metrics")
print(f"9. Metrics: {r.status_code} OK ({len(r.text)} bytes)")

# 10. Swagger docs
r = httpx.get(f"{base}/docs")
print(f"10. Swagger docs: {r.status_code} OK")

print()
print("--- Provider IDs (use for simulate/failure test) ---")
print(f"OpenRouter:  {groq_id}")
print(f"Gemini:      {gemini_id}")
print(f"HuggingFace: {hf_id}")
print(f"Prompt:      {prompt_id}")
