$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$sdk = Join-Path $root '.tools/pvsneslib/pvsneslib'
$bash = 'C:/msys64/usr/bin/bash.exe'
if (!(Test-Path $bash) -or !(Test-Path $sdk)) {
    throw 'MSYS2 and PVSnesLib must be installed. See README.md.'
}
$sample = Join-Path $root 'build/hello-world'
if (!(Test-Path "$sample/Makefile")) {
    New-Item -ItemType Directory -Force "$sample/src" | Out-Null
    Copy-Item "$sdk/snes-examples/hello_world/Makefile" "$sample/Makefile"
    Copy-Item "$sdk/snes-examples/hello_world/src/hello_world.c" "$sample/src/hello_world.c"
}
$env:MSYSTEM = 'UCRT64'
$env:CHERE_INVOKING = '1'
$env:GFC_ROOT = $root
$env:GFC_SDK = $sdk
& $bash --login "$PSScriptRoot/build-sample.sh"
if ($LASTEXITCODE -ne 0) { throw 'SNES sample build failed.' }
Write-Host "ROM: $root/build/hello-world/hello_world.sfc"
