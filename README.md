# 🚀 High-Availability LLM Token Generation Limiter & Fallback Proxy

A resilient, high-availability AI proxy built with **FastAPI** and **Python (`httpx`)**. This service routes incoming prompt requests to a primary LLM provider (**OpenAI**) and automatically fails over to a secondary provider (**Groq**) whenever rate limits (`429`), authentication errors, or server downtimes (`5xx`) are detected.

---

## ✨ Features

- **⚡ Automatic Failover & High Availability:** Automatically detects failures from OpenAI (e.g., `429 Insufficient Quota`, `503 Service Unavailable`) and routes traffic seamlessly to a free alternative model on Groq with zero downtime.
- **🔍 Health & Diagnostic Endpoint:** Includes a `/test-connections` route that checks connectivity and key validity against provider API endpoints without consuming token usage.
- **📊 Token Metrics & Cost Tracking:** Dynamically extracts `prompt_tokens`, `completion_tokens`, and `total_tokens` from API payloads and estimates request costs in real-time.
- **🛡️ Secure Environment Handling:** Uses `python-dotenv` for clean API key management without hardcoded credentials.

---

## 🛠️ Tech Stack

- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **HTTP Client:** Async `httpx`
- **Data Validation:** Pydantic
- **Environment Management:** `python-dotenv`

---

## ⚙️ Project Architecture