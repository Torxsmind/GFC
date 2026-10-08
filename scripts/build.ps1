param([switch]$Clean)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$sdk = Join-Path $root '.tools/pvsneslib/pvsneslib'
$bash = 'C:/msys64/usr/bin/bash.exe'
if (!(Test-Path $bash) -or !(Test-Path $sdk)) {
    throw 'MSYS2 and PVSnesLib must be installed. See README.md.'
}
$env:MSYSTEM = 'UCRT64'
$env:CHERE_INVOKING = '1'
$env:GFC_ROOT = $root
$env:GFC_SDK = $sdk
$env:GFC_CLEAN = if ($Clean) { '1' } else { '0' }
& $bash --login "$PSScriptRoot/build.sh"
if ($LASTEXITCODE -ne 0) { throw 'SNES game build failed.' }
New-Item -ItemType Directory -Force "$root/build" | Out-Null
Copy-Item "$root/gfc.sfc" "$root/build/gfc.sfc" -Force
Copy-Item "$root/gfc.sym" "$root/build/gfc.sym" -Force
Write-Host "ROM: $root/build/gfc.sfc"
