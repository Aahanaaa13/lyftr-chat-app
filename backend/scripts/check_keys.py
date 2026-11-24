import os
import litellm

keys = [k.strip() for k in os.getenv("LLM_API_KEYS", "").split(",") if k.strip()]
model = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
print(f"model={model}, keys={len(keys)}")
for i, key in enumerate(keys, 1):
    try:
        r = litellm.completion(model=model, api_key=key, num_retries=0, timeout=30,
                               messages=[{"role": "user", "content": "Say hi"}], max_tokens=20)
        print(f"key_{i}: OK -> {r.choices[0].message.content!r}")
    except Exception as e:
        print(f"key_{i}: FAILED {type(e).__name__}: {str(e).replace(key, '***')[:400]}")
