param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [Parameter(Mandatory=$true)][string]$OutputZip
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path (Join-Path $AppRoot 'pyproject.toml'))) { throw "Not a project root: $AppRoot" }
$stage = Join-Path ([System.IO.Path]::GetTempPath()) ('geo-server2-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stage | Out-Null
try {
  $items = @('config','deploy','docs','server2','shared','pyproject.toml','uv.lock','README.md')
  foreach ($item in $items) {
    $src = Join-Path $AppRoot $item
    if (Test-Path $src) { Copy-Item -Recurse -Force $src (Join-Path $stage $item) }
  }
  Get-ChildItem -Recurse -File $stage | Where-Object { $_.FullName -match '\\(runtime|data|\.venv|\.git|__pycache__|deploy\\offline\\packages)\\' -or $_.Extension -match '\.(pyc|hc|vc|vhd|vhdx|tif|tiff|shp|dbf|shx|osgb|pem|key|p12|jks)$' } | Remove-Item -Force -ErrorAction SilentlyContinue
  Get-ChildItem -Recurse -Directory $stage | Where-Object { $_.Name -in @('runtime','data','.venv','.git','__pycache__','packages') -or $_.FullName -match 'deploy[\\/]offline[\\/]packages' } | Sort-Object FullName -Descending | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  $parent = Split-Path $OutputZip -Parent
  if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  if (Test-Path $OutputZip) { Remove-Item -Force $OutputZip }
  Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $OutputZip -CompressionLevel Optimal
  Write-Output "Created code-only deployment package: $OutputZip"
  Write-Output 'Excluded: customer data, runtime models, virtual environments, VeraCrypt volumes, secrets and certificates.'
} finally {
  Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
}
