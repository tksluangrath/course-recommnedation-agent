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
