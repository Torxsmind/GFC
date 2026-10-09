$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$exe = Join-Path $root '.tools/mesen/Mesen.exe'
if (!(Test-Path "$root/build/gfc.sfc")) { throw 'Build the game first: scripts/build.ps1' }
if (!(Test-Path $exe)) { throw 'Mesen is not installed in .tools/mesen.' }
# Initialize this portable copy only; retain any existing user settings.
if (!(Test-Path "$root/.tools/mesen/settings.json")) {
    Copy-Item "$PSScriptRoot/mesen-settings.json" "$root/.tools/mesen/settings.json"
}
New-Item -ItemType Directory -Force "$root/build/screenshots" | Out-Null
$env:GFC_ROOT = $root
$arguments = @('--testRunner', '--doNotSaveSettings', '--timeout=120',
    '--snes.port1.type=SnesController',
    '--debug.scriptwindow.allowioosaccess=true',
    "$root/tests/verify-rom.lua", "$root/build/gfc.sfc")
# I/O access is enabled only for this trusted local test script, in this process.
$p = Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "$root/build/mesen-test.log" `
    -RedirectStandardError "$root/build/mesen-test-error.log"
$null = $p.Handle
if (!$p.WaitForExit(125000)) {
    Stop-Process -Id $p.Id
    throw 'Mesen verification timed out. Inspect build/verification.txt.'
}
if (Test-Path "$root/build/verification.txt") { Get-Content "$root/build/verification.txt" }
if ($p.ExitCode -ne 0) {
    Get-Content "$root/build/mesen-test-error.log"
    throw "ROM checks failed (exit $($p.ExitCode))."
}
