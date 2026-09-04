param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [switch]$RequireTrustMark
)
$ErrorActionPreference = 'Stop'
function Fail($message) { throw $message }
if (-not (Test-Path $AppRoot)) { Fail "AppRoot not found: $AppRoot" }
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) { Fail 'Python 3.11 x64 not found in PATH' }
$version = (& python --version 2>&1 | Out-String).Trim()
if ($version -notmatch 'Python 3\.11\.') { Fail "Python 3.11 required, got: $version" }
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($null -eq $uv) { Fail 'uv not found in PATH. Install uv or use the approved offline installation procedure.' }
$mainPython = Join-Path $AppRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $mainPython)) { Fail "Main venv missing: $mainPython. Run install_server2.ps1 first." }
& $mainPython -c "import fastapi, uvicorn, rasterio, pyproj, shapefile, numpy, scipy, PIL, cryptography; print('main dependencies: OK')"
if ($LASTEXITCODE -ne 0) { Fail 'Main Python dependencies are incomplete' }
$envFile = Join-Path (Split-Path $AppRoot -Parent) 'server2.env'
if (-not (Test-Path $envFile)) { Fail "Config missing: $envFile" }
$settings = @{}
foreach ($line in Get-Content $envFile) {
  if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
  $pair = $line -split '=', 2
  $settings[$pair[0].Trim()] = $pair[1].Trim()
}
foreach ($name in @('GDS_WORKSPACE','GDS_AUDIT_DIR','GDS_TASK_DATABASE','GDS_INPUT_ROOT','GEO_SECURITY_SERVER1_TOKEN','GDS_WORKSPACE_KEY')) {
  if (-not $settings.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($settings[$name]) -or $settings[$name] -like 'REPLACE_*') { Fail "Missing config value: $name" }
}
foreach ($pathName in @('GDS_WORKSPACE','GDS_AUDIT_DIR','GDS_INPUT_ROOT')) {
  if (-not (Test-Path $settings[$pathName])) { Write-Output "WARN path not created yet: $pathName=$($settings[$pathName])" }
}
if ($RequireTrustMark) {
  foreach ($name in @('GDS_TRUSTMARK_PYTHON','GDS_TRUSTMARK_RUNNER')) {
    if (-not $settings.ContainsKey($name) -or -not (Test-Path $settings[$name])) { Fail "TrustMark path missing: $name=$($settings[$name])" }
  }
  & $settings['GDS_TRUSTMARK_PYTHON'] $settings['GDS_TRUSTMARK_RUNNER'] --help 2>$null
  if ($LASTEXITCODE -eq 0) { Write-Output 'TrustMark runner: reachable' } else { Write-Output 'WARN TrustMark runner has no --help command; path exists' }
}
Write-Output 'server2 configuration check: OK'
