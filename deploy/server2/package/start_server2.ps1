param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [string]$EnvFile = (Join-Path $AppRoot 'server2.env')
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $EnvFile)) { throw "Missing config file: $EnvFile" }
foreach ($line in Get-Content $EnvFile) {
  if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
  $pair = $line -split '=', 2
  [Environment]::SetEnvironmentVariable($pair[0].Trim(), $pair[1].Trim(), 'Process')
}
$required = @('GDS_WORKSPACE','GDS_AUDIT_DIR','GDS_TASK_DATABASE','GDS_INPUT_ROOT','GEO_SECURITY_SERVER1_TOKEN','GDS_WORKSPACE_KEY','GDS_TRUSTMARK_PYTHON','GDS_TRUSTMARK_RUNNER')
foreach ($name in $required) {
  $value = [Environment]::GetEnvironmentVariable($name, 'Process')
  if ([string]::IsNullOrWhiteSpace($value) -or $value -like 'REPLACE_*') { throw "Missing required setting: $name" }
}
New-Item -ItemType Directory -Force -Path $env:GDS_WORKSPACE,$env:GDS_AUDIT_DIR,$env:GDS_INPUT_ROOT,(Split-Path $env:GDS_TASK_DATABASE) | Out-Null
$env:PYTHONPATH = Join-Path $AppRoot 'server2\pipeline'
Push-Location (Join-Path $AppRoot 'server2\pipeline')
try {
  & (Join-Path $AppRoot '.venv\Scripts\python.exe') -m uvicorn geo_security.serve:app --host $env:GDS_SERVER2_HOST --port $env:GDS_SERVER2_PORT
} finally { Pop-Location }
