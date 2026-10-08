param(
    [ValidateSet('Mesen', 'LibreSprite', 'Tiled', 'OpenMPT')]
    [string]$Tool = 'Mesen',
    [string]$Rom
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$paths = @{
    Mesen = "$root/.tools/mesen/Mesen.exe"
    LibreSprite = "$root/.tools/libresprite/libresprite.exe"
    Tiled = 'C:/Program Files/Tiled/tiled.exe'
    OpenMPT = 'C:/Program Files/OpenMPT/OpenMPT.exe'
}
$exe = $paths[$Tool]
if ($Tool -eq 'OpenMPT' -and !(Test-Path $exe)) {
    $exe = "$env:LOCALAPPDATA/Programs/OpenMPT/bin/amd64/OpenMPT.exe"
}
if (!(Test-Path $exe)) { throw "Tool not found: $exe" }
if ($Tool -eq 'Mesen' -and !(Test-Path "$root/.tools/mesen/settings.json")) {
    Copy-Item "$PSScriptRoot/mesen-settings.json" "$root/.tools/mesen/settings.json"
}
if ($Rom) { & $exe $Rom } else { & $exe }
