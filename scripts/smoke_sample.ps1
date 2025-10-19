Param()
$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot/../queryshield/sample-django-app"
$env:DJANGO_SETTINGS_MODULE = 'sample_django_app.settings'
$env:DB_ENGINE = 'django.db.backends.postgresql'
$env:DB_NAME = 'appdb'
$env:DB_USER = 'postgres'
$env:DB_PASSWORD = 'postgres'
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '5432'
python -m pip install -e ../probe -e ../cli psycopg2-binary | Out-Null
python manage.py migrate
Write-Host '== BEFORE (N+1) =='
queryshield analyze --runner=django --output ./.queryshield/before.json
Write-Host 'Expecting budgets to fail'
try {
  queryshield budget-check --budgets ../queryshield.yml --report ./.queryshield/before.json
  throw 'Expected budgets to fail'
} catch {}
Write-Host '== AFTER (optimized) =='
queryshield analyze --runner=django --output ./.queryshield/after.json
queryshield budget-check --budgets ../queryshield.yml --report ./.queryshield/after.json
Write-Host '== Overhead & Top DDL =='
python - <<PY
import json
data=json.load(open('.queryshield/after.json'))
run=data.get('run',{})
dur=float(run.get('duration_ms') or 0.0)
exp=float(run.get('explain_runtime_ms') or 0.0)
print('Duration: %.1f ms, EXPLAIN: %.1f ms, Overhead: %.1f%%' % (dur, exp, 100*exp/dur if dur else 0.0))
PY
Get-Content ./.queryshield/ddl-suggestions.txt -TotalCount 10 | ForEach-Object { $_ }

