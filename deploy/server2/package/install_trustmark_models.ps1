param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [Parameter(Mandatory=$true)][string]$InstallRoot,
  [Parameter(Mandatory=$true)][string]$ModelSource
)
$ErrorActionPreference = 'Stop'
$tmVenv = Join-Path $InstallRoot 'trustmark_venv'
$tmPython = Join-Path $tmVenv 'Scripts\python.exe'
if (-not (Test-Path $tmPython)) { throw "TrustMark venv missing: $tmPython. Run install_server2.ps1 first." }
$models = Join-Path $InstallRoot 'trustmark_models'
New-Item -ItemType Directory -Force -Path $models | Out-Null
$required = @('encoder_Q.ckpt','decoder_Q.ckpt','trustmark_Q.yaml','trustmark_bbox_Q.ckpt','trustmark_bbox_Q.yaml')
foreach ($name in $required) {
  $src = Join-Path $ModelSource $name
  if (-not (Test-Path $src)) { throw "TrustMark model file missing: $src" }
  Copy-Item -Force $src (Join-Path $models $name)
}
$hashes = @{
  'encoder_Q.ckpt'='700328b8754db934b2f6cb5e5185d81f'
  'decoder_Q.ckpt'='4ced90e9cfe13e3295ad082887fe9187'
  'trustmark_Q.yaml'='fe40df84a7feeebfceb7a7678d7e6ec6'
  'trustmark_bbox_Q.ckpt'='9d15428a33e15140ea16aa378416d304'
  'trustmark_bbox_Q.yaml'='749b0d62106f8f6648e6f781c3143105'
}
foreach ($name in $required) {
  $actual = (Get-FileHash (Join-Path $models $name) -Algorithm MD5).Hash.ToLower()
  if ($actual -ne $hashes[$name]) { throw "MD5 mismatch for ${name}: $actual" }
}
# The runner uses trustmark's package-local models directory. Keep a private copy
# in the isolated venv package so the production path is deterministic and offline.
$packageModels = Join-Path (& $tmPython -c "import pathlib,trustmark; print(pathlib.Path(trustmark.__file__).parent / 'models')")
New-Item -ItemType Directory -Force -Path $packageModels | Out-Null
foreach ($name in $required) { Copy-Item -Force (Join-Path $models $name) (Join-Path $packageModels $name) }
Write-Output "TrustMark models verified and installed: $models"
