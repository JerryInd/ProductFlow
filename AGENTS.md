# ProductFlow AI — Agent Conventions

## Project structure
```
/productflow
  backend/          # Python FastAPI (uvicorn)
  frontend/         # SvelteKit + Cloudflare Pages
  whatsapp-bridge/  # Node.js Baileys WhatsApp bridge
  database/         # SQLite schema + migrations
  models/           # GGUF model files (gitignored)
  sessions/         # WhatsApp session data (gitignored)
  media-cache/      # Temp media storage (gitignored)
  scripts/          # setup.sh, start.sh, recover.sh
```

## Stack
- **Backend**: Python 3.11+, FastAPI, SQLite (aiosqlite), uvicorn
- **Frontend**: SvelteKit 2, TypeScript, Cloudflare Pages adapter
- **WhatsApp**: `@whiskeysockets/baileys` (no browser needed)
- **AI**: llama.cpp subprocess, SmolLM2-135M GGUF (load→rewrite→unload)
- **Tunnel**: Cloudflare Tunnel (dashboard at productflow.pages.dev)
- **Platform**: Raspberry Pi Zero 2 W (512MB RAM, 32GB SD)

## Conventions
- Python: flat services/ (no ORM, raw SQLite), snake_case, type hints
- Frontend: Svelte 5 runes ($state, $derived, $effect), dark theme
- API: `/api/{resource}`, JSON in/out, status codes
- DB: WAL mode, foreign keys, ISO timestamps
- WhatsApp: Baileys bridge sends messages to `/api/whatsapp/message`
- Pi optimization: model loaded on demand, swap 1024MB, max RAM 450MB

## Commands
```bash
# backend (Pi/Linux)
cd backend && ../.venv/bin/uvicorn app.main:app --port 8000

# backend (Windows)
cd backend && ..\.venv\Scripts\uvicorn app.main:app --port 8000

# frontend
cd frontend && npm run build

# whatsapp
cd whatsapp-bridge && node bridge.js

# health check
curl http://localhost:8000/api/health
```

## Key files
- `backend/app/config.py` — all paths and Pi tuning params
- `backend/app/services/pipeline_service.py` — core orchestrator
- `backend/app/services/ai_engine.py` — llama.cpp wrapper (thread-safe, load→rewrite→unload)
- `backend/app/services/pricing_engine.py` — price rule executor
- `backend/app/services/recovery_service.py` — boot-time recovery
- `backend/app/services/product_collector.py` — media collector with idle timeout and max size
- `frontend/src/lib/api.ts` — all API client functions

## Pi Zero 2 W load notes
- **RAM budget**: Python ~55MB, Node ~80MB, llama.cpp peak ~200MB → total ~335MB (under 450MB limit)
- **AI lock**: `threading.Lock` in AI engine serializes all rewrites — only one llama.cpp runs at a time
- **Model mode**: `--no-mmap --threads 4 -ngl 0` — no GPU offload, loads into RAM on demand
- **Timeout**: 120s for llama.cpp (cold start on Pi takes 30-60s)
- **Collector**: Background loop every 15s checks for expired collections; 5min absolute max idle
- **Logs**: Rotating file handler (5MB x 2 backups) to prevent SD card fill
- **Workers**: `--workers 1 --no-access-log` — single process, no access log I/O
- **Bridge**: `--max-old-space-size=128` — Node.js heap capped at 128MB
- **Swappiness**: `vm.swappiness=10` — prefer RAM, avoid SD card swap wear
- **Docker**: `mem_limit: 256m` (backend), `128m` (bridge) — hard caps against OOM
- **Retries**: Bridge retries API calls with exponential backoff (1s→2s→4s→8s→16s)
- **Async dispatch**: `/api/whatsapp/message` returns immediately via `BackgroundTasks`
