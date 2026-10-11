# PatchCourt — full run commands (Docker + dashboard)
# From repo root: D:\CIT SEM\mainproj1\patchcourt
# 1. Build sandbox image (optional but recommended)
docker compose build sandbox

# 2. Start core services (postgres, redis, qdrant, api)
docker compose up -d

# 3. Start worker + dashboard (optional but needed for async/webhook + UI)
docker compose --profile worker --profile dashboard up -d

# 4. Check health
curl http://localhost:8000/health
curl http://localhost:8000/api/sonar/health

# 5. Run demo review
curl -X POST http://localhost:8000/api/review/demo

# 6. Run comparison demo (SonarQube vs PatchCourt)
curl http://localhost:8000/api/comparison/demo

# 7. Run benchmark via API
curl -X POST http://localhost:8000/api/benchmark/run

# 8. Dashboard
# Open http://localhost:3001

# CLI alternatives (local)
python -m patchcourt review --demo
python -m patchcourt benchmark
python -m patchcourt benchmark --quiet
