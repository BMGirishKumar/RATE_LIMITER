import os
import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="LLM Fallback with OpenAI and Groq", version="2.3")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class PromptRequest(BaseModel):
    prompt: str = Field(..., description="The input text prompt for the LLM")
    max_tokens: int = Field(150, description="Max tokens to generate")

# Diagnostic Endpoint to verify keys
@app.get("/test-connections")
async def test_connections():
    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            openai_resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
            )
            results["openai"] = {"status": "Connected & Key Valid", "code": openai_resp.status_code}
        except Exception as e:
            results["openai"] = {"status": "Unreachable", "error": str(e)}

        try:
            groq_resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"}
            )
            results["groq"] = {"status": "Connected & Key Valid", "code": groq_resp.status_code}
        except Exception as e:
            results["groq"] = {"status": "Unreachable", "error": str(e)}

    return results

# Primary Call: OpenAI
async def call_openai(prompt: str, max_tokens: int) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code in [401, 403, 429] or response.status_code >= 500:
            raise HTTPException(status_code=response.status_code, detail=f"OpenAI Error: {response.text}")
        response.raise_for_status()
        data = response.json()
        
        usage = data.get("usage", {})
        return {
            "content": data["choices"][0]["message"]["content"],
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }

# Secondary Call: Groq using current stable model ID
# Secondary Call: Groq using a stable production model ID
# Secondary Call: Groq using the active supported model ID
async def call_groq(prompt: str, max_tokens: int) -> dict:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-oss-20b",  # Active self-serve production model on Groq
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Groq API Error: {response.text}")
        response.raise_for_status()
        data = response.json()
        
        usage = data.get("usage", {})
        return {
            "content": data["choices"][0]["message"]["content"],
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        } 
@app.post("/generate")
async def generate_text(request: PromptRequest):
    """
    Attempts OpenAI first. If it fails, falls back to Groq.
    """
    try:
        print("Trying primary provider: OpenAI...")
        result = await call_openai(request.prompt, request.max_tokens)
        provider = "openai"
        cost_usd = 0.00001
        
    except Exception as e:
        print(f"OpenAI failed ({e}). Falling back to Groq...")
        
        try:
            result = await call_groq(request.prompt, request.max_tokens)
            provider = "groq (free tier)"
            cost_usd = 0.0
        except Exception as fallback_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Both primary and fallback providers failed. Details: {str(fallback_error)}"
            )

    return {
        "provider": provider,
        "response": result["content"],
        "usage": {
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
            "estimated_cost_usd": cost_usd
        }
    }