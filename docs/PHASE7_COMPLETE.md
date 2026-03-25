# Phase 7 — Docker Compose Deployment ✅

Phase 7 wraps the whole project in Docker so anyone can run it with a single command — no Python install, no Ollama install, no manual data pipeline. The goal was to make "getting it running" a completely solved problem.

```bash
docker compose up --build
```

Open `http://localhost:8501`. Done.

---

## How it's structured

Two containers, orchestrated by Docker Compose:

| Container | Image | What it does |
|---|---|---|
| `ollama` | `ollama/ollama` (official) | Runs Llama 3.1 locally on port 11434 |
| `app` | Built from `Dockerfile` | Python 3.11 + all dependencies + Streamlit on port 8501 |

The `app` container waits for `ollama` to pass its healthcheck before starting — so the agent is never initialized before the LLM is actually ready to respond.

### The model download problem

Llama 3.1 is ~4.7 GB. Baking it into the image would make the image enormous and require a re-download every time you rebuild. Instead, the weights are stored in a named Docker volume (`ollama_data`). The download happens once via `docker-entrypoint.sh` on first run. Every subsequent `docker compose up` skips the download and starts in seconds.

### Data persistence

The `./data` directory is mounted as a volume into the container at `/app/data`. This means:
- The existing SQLite database and ChromaDB vector store carry over immediately — no re-running the data pipeline inside Docker
- User profiles created in Docker persist between container restarts
- The same `data/` folder works for both Docker and local runs interchangeably

### Container networking

Both containers share a Docker Compose network. The `app` container reaches Ollama at `http://ollama:11434` (the service name) instead of `localhost`. This required one code change: `llm_config.py` now reads `OLLAMA_HOST` from the environment, defaulting to `http://localhost:11434` so local runs still work unchanged.

---

## Files created

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

Python 3.11-slim was chosen deliberately — it sidesteps the Windows Python 3.13 + PyTorch DLL issue that affects local development. `curl` is installed because the entrypoint script needs it to trigger the model pull. `data/` is intentionally excluded from the image (it's mounted as a volume).

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

A few decisions worth noting: `condition: service_healthy` means the app waits for Ollama to actually respond, not just to have started. The `.env` file is mounted read-only so the container can read it but can't accidentally overwrite it. `restart: unless-stopped` means the app container comes back automatically if it crashes.

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

`stream:false` keeps the pull synchronous — the script waits for the full download before proceeding to start Streamlit. `--server.address=0.0.0.0` is required so Streamlit binds to all interfaces inside the container, not just localhost. Without it the port mapping doesn't work.

## Files modified

`src/utils/llm_config.py` — one line added:
```python
# Before
llm = ChatOllama(model=LLMConfig.OLLAMA_MODEL, temperature=...)

# After
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
llm = ChatOllama(model=LLMConfig.OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=...)
```

The default keeps local runs working. Docker overrides it via the compose environment block.

---

## What to expect on first run

1. Docker builds the `app` image (installs all Python dependencies — takes a few minutes the first time)
2. The `ollama` container starts and passes its healthcheck
3. The `app` container starts and `docker-entrypoint.sh` runs
4. The script pulls Llama 3.1 from Ollama's servers (~4.7 GB — can take a while depending on your connection)
5. Streamlit starts and the app is available at `http://localhost:8501`

Every run after that: the model is already in the `ollama_data` volume, so the pull is a no-op and the whole stack is up in a few seconds.

---

**Status**: All 7 phases complete. The project is feature-complete.
*Updated: February 2026*
