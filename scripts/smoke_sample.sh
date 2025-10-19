#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."/queryshield/sample-django-app
export DJANGO_SETTINGS_MODULE=sample_django_app.settings
export DB_ENGINE=django.db.backends.postgresql
export DB_NAME=appdb
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=127.0.0.1
export DB_PORT=5432
python -m pip install -e ../probe -e ../cli psycopg2-binary >/dev/null
python manage.py migrate
echo "== BEFORE (N+1) =="
queryshield analyze --runner=django --output .queryshield/before.json
set +e
queryshield budget-check --budgets ../queryshield.yml --report .queryshield/before.json
rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo "Expected budgets to fail"; exit 1; fi
echo "== AFTER (optimized) =="
queryshield analyze --runner=django --output .queryshield/after.json
queryshield budget-check --budgets ../queryshield.yml --report .queryshield/after.json
echo "== Overhead & Top DDL =="
python - <<'PY'
import json
data=json.load(open('.queryshield/after.json'))
run=data.get('run',{})
dur=float(run.get('duration_ms') or 0.0)
exp=float(run.get('explain_runtime_ms') or 0.0)
print('Duration: %.1f ms, EXPLAIN: %.1f ms, Overhead: %.1f%%' % (dur, exp, 100*exp/dur if dur else 0.0))
PY
head -n 10 .queryshield/ddl-suggestions.txt || true

