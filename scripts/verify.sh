#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile $(find backend/app evaluation -name '*.py')
python3 - <<'PY'
import yaml
with open('docker-compose.yml') as f:
    compose = yaml.safe_load(f)
assert set(compose['services']) == {'qdrant', 'postgres', 'redis', 'backend', 'worker', 'frontend'}
assert compose['networks']['shodh']['name'] == 'shodh'
print('Static repository checks passed.')
PY

if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
  echo 'Docker Compose config passed.'
else
  echo 'Docker is not installed; skipped docker compose config.'
fi
