param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [Parameter(Mandatory=$true)][string]$InstallRoot,
  [string]$BundleRoot = (Split-Path $PSScriptRoot -Parent)
)
$ErrorActionPreference = 'Stop'
function Fail($message) { throw $message }
$mainWheels = Join-Path $BundleRoot 'main_wheels'
$tmWheels = Join-Path $BundleRoot 'trustmark_wheels'
$mainReq = Join-Path $BundleRoot 'main_requirements.txt'
$tmReq = Join-Path $BundleRoot 'trustmark_offline_requirements.txt'
$models = Join-Path $BundleRoot 'models'
foreach ($path in @($mainWheels,$tmWheels,$mainReq,$tmReq,$models)) {
  if (-not (Test-Path $path)) { Fail "Offline bundle item missing: $path" }
}
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) { Fail 'Python 3.11 x64 must be installed before offline setup' }
$version = (& python --version 2>&1 | Out-String).Trim()
if ($version -notmatch 'Python 3\.11\.') { Fail "Python 3.11 required, got: $version" }
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($null -eq $uv) { Fail 'uv must be installed before offline setup' }
$mainVenv = Join-Path $AppRoot '.venv'
& uv venv $mainVenv --python python
$mainPython = Join-Path $mainVenv 'Scripts\python.exe'
& uv pip install --offline --no-index --find-links $mainWheels --python $mainPython -r $mainReq
if ($LASTEXITCODE -ne 0) { Fail 'Offline main environment installation failed' }
$tmVenv = Join-Path $InstallRoot 'trustmark_venv'
& uv venv $tmVenv --python python
$tmPython = Join-Path $tmVenv 'Scripts\python.exe'
& uv pip install --offline --no-index --find-links $tmWheels --python $tmPython --no-deps -r $tmReq
if ($LASTEXITCODE -ne 0) { Fail 'Offline TrustMark dependency installation failed' }
# OmegaConf 2.3.1 declares antlr4 4.9.*, which is a source-only package on
# domestic mirrors. Replace the candidate 4.11 wheel with the verified 4.9.3 source.
& uv pip uninstall --python $tmPython antlr4-python3-runtime
$antlr = Get-ChildItem (Join-Path $tmWheels 'antlr4-python3-runtime-4.9.3.tar.gz')
& uv pip install --offline --no-index --find-links $tmWheels --python $tmPython $antlr.FullName
if ($LASTEXITCODE -ne 0) { Fail 'Offline antlr4 4.9.3 installation failed' }
& uv pip install --offline --no-index --find-links $tmWheels --python $tmPython --no-deps (Join-Path $tmWheels 'trustmark-0.9.0.tar.gz')
if ($LASTEXITCODE -ne 0) { Fail 'Offline TrustMark installation failed' }
$modelsTarget = Join-Path (& $tmPython -c "import pathlib,trustmark; print(pathlib.Path(trustmark.__file__).parent / 'models')")
New-Item -ItemType Directory -Force -Path $modelsTarget | Out-Null
foreach ($model in Get-ChildItem -File $models) { Copy-Item -Force $model.FullName (Join-Path $modelsTarget $model.Name) }
Write-Output 'Offline server2 Python installation completed.'
Write-Output "Main venv: $mainVenv"
Write-Output "TrustMark venv: $tmVenv"
Write-Output "Models: $modelsTarget"
Write-Output 'Next: copy server2.env.example to AppRoot\server2.env, fill secrets/paths, then run check_server2.ps1.'
