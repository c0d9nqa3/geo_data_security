param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [Parameter(Mandatory=$true)][string]$InstallRoot
)
$ErrorActionPreference = 'Stop'
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) { throw 'Python 3.11 x64 not found in PATH' }
$version = (& python --version 2>&1 | Out-String).Trim()
if ($version -notmatch 'Python 3\.11\.') { throw "Python 3.11 required, got: $version" }
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($null -eq $uv) { throw 'uv not found in PATH' }
$mainVenv = Join-Path $AppRoot '.venv'
& uv venv $mainVenv --python python
& uv pip install --python (Join-Path $mainVenv 'Scripts\python.exe') -e $AppRoot
if ($LASTEXITCODE -ne 0) { throw 'Main server2 dependency installation failed' }
$tmVenv = Join-Path $InstallRoot 'trustmark_venv'
& uv venv $tmVenv --python python
$tmPython = Join-Path $tmVenv 'Scripts\python.exe'
# Install the published TrustMark package, not a runtime source tree that is
# intentionally excluded from the Git deployment package.
& uv pip install --python $tmPython --index-url https://mirrors.aliyun.com/pypi/simple `
  'numpy<2' 'trustmark==0.9.0' 'rasterio>=1.4,<2' 'pyproj>=3.7,<4' `
  'opencv-python-headless==4.10.0.84'
if ($LASTEXITCODE -ne 0) { throw 'TrustMark environment dependency installation failed' }
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Write-Output "Main environment ready: $mainVenv"
Write-Output "TrustMark environment ready: $tmVenv"
Write-Output 'Run install_trustmark_models.ps1 with a verified offline model directory before starting.'
