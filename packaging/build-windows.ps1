# Build the frozen Windows executable and zip it.
#
#   pwsh packaging/build-windows.ps1 -Version 0.1.0
#
# Requires: pyinstaller (pip), Python 3.12 x64 on PATH.
param(
    [string]$Version = "0.1.0",
    [string]$Arch = "x64"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "== version $Version, $Arch =="
Remove-Item -Recurse -Force build/pyinstaller, dist -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path dist/packages | Out-Null

# --collect-all is required for the .pptx/.docx templates and pdfminer cmaps:
# without them the build succeeds and the program fails at runtime.
python -m PyInstaller `
    --noconfirm --clean --onedir --console `
    --name pdftoall `
    --paths src `
    --collect-all pdfplumber `
    --collect-all pdfminer `
    --collect-all pptx `
    --collect-all docx `
    --collect-all openpyxl `
    --collect-data pypdf `
    --distpath dist --workpath build/pyinstaller --specpath build/pyinstaller `
    packaging/pyinstaller_entry.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "== smoke test =="
& dist/pdftoall/pdftoall.exe --version
if ($LASTEXITCODE -ne 0) { throw "frozen binary does not start" }
& dist/pdftoall/pdftoall.exe info samples/quarterly-review.pdf
if ($LASTEXITCODE -ne 0) { throw "frozen binary cannot parse a PDF" }

Copy-Item packaging/WINDOWS-README.txt dist/pdftoall/README.txt

Write-Host "== archive =="
Compress-Archive -Path dist/pdftoall -DestinationPath "dist/packages/pdftoall-$Version-windows-$Arch.zip" -Force
Get-ChildItem dist/packages | Format-Table Name, Length
