# Phase 7 Complete — Docker Compose Deployment

## Summary

Phase 7 wraps the entire project in a Docker Compose setup so anyone can run the app with a single command — no Python install, no Ollama install, no manual data pipeline. Everything is containerized and self-contained.

**Run the app:**
```bash
docker compose up --build   # first time (~4.7 GB model download)
docker compose up           # after that
```
Open `http://localhost:8501`

---

## What Was Built

### Two-Container Architecture

| Service | Image | Purpose |
|---|---|---|
| `ollama` | `ollama/ollama` (official) | Runs Llama 3.1 locally, serves on port 11434 |
| `app` | Built from `Dockerfile` | Python 3.11 + all dependencies, runs Streamlit on port 8501 |

The `app` container waits for `ollama` to pass its healthcheck before starting, so the agent is never initialized before the LLM is ready.

### Model Caching

Llama 3.1 weights (~4.7 GB) are stored in a named Docker volume (`ollama_data`). The download happens once on first run — subsequent `docker compose up` calls start in seconds.

### Data Persistence

The `./data` directory is mounted as a volume into the container at `/app/data`. This means:
- No ETL re-run needed — existing SQLite and ChromaDB data carry over immediately
- User profiles created inside Docker persist between container restarts
- The same `data/` folder works for both Docker and manual local runs

### Container Networking

The two containers share a default Docker Compose network. The `app` service reaches Ollama via the service name (`http://ollama:11434`) instead of `localhost`. This required one code change: `OLLAMA_HOST` env var support in `llm_config.py`.

---

## Files Created

| File | Description |
|---|---|
| `Dockerfile` | `python:3.11-slim` base, installs requirements, copies `src/` and `app/` |
| `docker-compose.yml` | Defines `ollama` + `app` services, volumes, healthcheck, and env vars |
| `docker-entrypoint.sh` | Pulls `llama3.1` via Ollama REST API on first run, then starts Streamlit |
| `.dockerignore` | Excludes `data/`, `.env`, `__pycache__`, `.git` from the image |

## Files Modified

| File | Change |
|---|---|
| `src/utils/llm_config.py` | Added `OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")` and passed it as `base_url` to both `Ollama()` and `ChatOllama()` |

---

## File Details

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY app/ app/

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8501
ENTRYPOINT ["./docker-entrypoint.sh"]
```

- `python:3.11-slim` chosen for compatibility (avoids Windows Python 3.13 PyTorch DLL issues)
- `curl` installed for the model pull in the entrypoint script
- `data/` is intentionally excluded (mounted as volume, not baked into image)

### `docker-compose.yml`

```yaml
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:11434/api/version"]
      interval: 10s
      timeout: 5s
      retries: 10

  app:
    build: .
    ports:
      - "8501:8501"
    depends_on:
      ollama:
        condition: service_healthy
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    environment:
      - OLLAMA_HOST=http://ollama:11434
    restart: unless-stopped

volumes:
  ollama_data:
```

Key decisions:
- `condition: service_healthy` — app waits for Ollama to actually be responding, not just started
- `.env` mounted read-only (`:ro`) so container can't accidentally overwrite it
- `restart: unless-stopped` — app container auto-restarts on crash

### `docker-entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "Pulling llama3.1 (skipped if already cached)..."
curl -s -X POST "${OLLAMA_HOST}/api/pull" \
     -H "Content-Type: application/json" \
     -d '{"name":"llama3.1","stream":false}'
echo ""

exec streamlit run app/streamlit_app.py \
     --server.address=0.0.0.0 \
     --server.port=8501 \
     --server.headless=true
```

- `stream:false` in the pull request keeps output clean (waits for download to complete before continuing)
- `--server.address=0.0.0.0` required so Streamlit binds to all interfaces, not just localhost inside the container
- `--server.headless=true` suppresses the "open browser" prompt

### `llm_config.py` change

```python
# Before
llm = ChatOllama(model=LLMConfig.OLLAMA_MODEL, temperature=...)

# After
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
llm = ChatOllama(model=LLMConfig.OLLAMA_MODEL, base_url=LLMConfig.OLLAMA_HOST, temperature=...)
```

Default remains `http://localhost:11434` so manual local runs still work unchanged. Docker sets `OLLAMA_HOST=http://ollama:11434` via the compose environment block.

---

## Verification

| Test | Expected |
|---|---|
| `docker compose up --build` | Pulls Llama 3.1, builds image, starts both containers |
| `http://localhost:8501` | Streamlit login screen appears |
| Login → chat → "recommend me some Python courses" | Agent responds using Ollama in the other container |
| Stop and restart with `docker compose up` | App starts in seconds, no model re-download |
| Profile data from previous session | Still present (data/ volume persists) |

---

**Status**: Phase 7 Complete
**Next**: Project feature-complete across all 7 phases
**Updated**: February 2026
