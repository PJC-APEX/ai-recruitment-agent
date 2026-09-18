# Start the durable ARQ resume-ingestion worker.
Set-Location $PSScriptRoot
# Some shells use DEBUG=release as a deployment label; Settings expects a
# boolean, so normalize it for the local worker just like start_server.ps1.
$env:DEBUG = "True"
& ".\.venv\Scripts\python.exe" -m arq app.jobs.worker.WorkerSettings
