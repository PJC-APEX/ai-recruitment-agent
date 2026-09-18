# Start FastAPI Server Script
Set-Location $PSScriptRoot
# Ensure the local development server receives a valid boolean setting even
# when the parent shell has DEBUG=release (or another deployment label).
$env:DEBUG = "True"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
