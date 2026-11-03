$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:OS -ne 'Windows_NT') { throw 'Build this package on Windows x64.' }
python -m pip install -e '.[desktop]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
python -m PyInstaller --noconfirm packaging/windows.spec
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
Compress-Archive -Path dist/PersonaWeave/* -DestinationPath dist/PersonaWeave-0.2.0-Windows-x64-Portable.zip -Force
$isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$isccPath = if ($isccCommand) { $isccCommand.Source } else { $null }
if (-not $isccPath) {
    $candidate = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) { $isccPath = $candidate }
}
if ($isccPath) {
    & $isccPath packaging/installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
} else { Write-Warning 'Inno Setup 6 not found. Portable app was built; install Inno Setup to build Setup.exe.' }
