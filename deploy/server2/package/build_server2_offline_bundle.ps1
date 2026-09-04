param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [Parameter(Mandatory=$true)][string]$OutputRoot
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path (Join-Path $AppRoot 'pyproject.toml'))) { throw "Not a project root: $AppRoot" }
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$codeZip = Join-Path $OutputRoot 'GeoDataSecurity-server2-code.zip'
$builder = Join-Path $AppRoot 'deploy\server2\package\build_server2_package.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $builder -AppRoot $AppRoot -OutputZip $codeZip
if ($LASTEXITCODE -ne 0) { throw 'Code package build failed' }
foreach ($name in @('main_wheels','trustmark_wheels','models','package','bootstrap')) {
  New-Item -ItemType Directory -Force -Path (Join-Path $OutputRoot $name) | Out-Null
}
$downloadRoot = Join-Path $AppRoot 'runtime\package_downloads'
Copy-Item -Recurse -Force (Join-Path $downloadRoot 'main_wheels') (Join-Path $OutputRoot 'main_wheels')
Copy-Item -Recurse -Force (Join-Path $downloadRoot 'trustmark_wheels') (Join-Path $OutputRoot 'trustmark_wheels')
Copy-Item -Force (Join-Path $downloadRoot 'main_requirements.txt') (Join-Path $OutputRoot 'main_requirements.txt')
Copy-Item -Force (Join-Path $downloadRoot 'trustmark_offline_requirements.txt') (Join-Path $OutputRoot 'trustmark_offline_requirements.txt')
Copy-Item -Force (Join-Path $AppRoot 'deploy\server2\package\*.ps1') (Join-Path $OutputRoot 'package')
Copy-Item -Force (Join-Path $AppRoot 'deploy\server2\package\*.example') (Join-Path $OutputRoot 'package')
Copy-Item -Force (Join-Path $AppRoot 'deploy\server2\package\*.md') (Join-Path $OutputRoot 'package')
$modelSource = Join-Path $AppRoot 'runtime\trustmark_source\python\trustmark\models'
foreach ($name in @('encoder_Q.ckpt','decoder_Q.ckpt','trustmark_Q.yaml','trustmark_bbox_Q.ckpt','trustmark_bbox_Q.yaml')) {
  Copy-Item -Force (Join-Path $modelSource $name) (Join-Path $OutputRoot 'models')
}
Copy-Item -Force (Join-Path $AppRoot 'runtime\server2_offline_bundle\bootstrap\*') (Join-Path $OutputRoot 'bootstrap') -ErrorAction SilentlyContinue
$manifest = Join-Path $OutputRoot 'FILELIST.txt'
Get-ChildItem -Recurse -File $OutputRoot | Where-Object { $_.Name -notin @('SHA256SUMS.txt','FILELIST.txt') } | ForEach-Object {
  "{0}`t{1} bytes" -f $_.FullName.Substring($OutputRoot.Length + 1), $_.Length
} | Sort-Object | Set-Content -Encoding UTF8 $manifest
Get-ChildItem -Recurse -File $OutputRoot | Where-Object { $_.Name -ne 'SHA256SUMS.txt' } | Get-FileHash -Algorithm SHA256 | ForEach-Object {
  "{0}  {1}" -f $_.Hash.ToLower(), $_.Path.Substring($OutputRoot.Length + 1)
} | Sort-Object | Set-Content -Encoding ASCII (Join-Path $OutputRoot 'SHA256SUMS.txt')
Write-Output "Offline bundle created: $OutputRoot"
