$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Python = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
& $Python -c "import sys; sys.exit('AI News Monitor packaging requires Python 3.11 or newer.') if sys.version_info < (3, 11) else None"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt -r requirements-dev.txt
& $Python -m pytest

Remove-Item -Recurse -Force build, dist, release -ErrorAction SilentlyContinue
Remove-Item -Force AI-News-Monitor-Windows.zip -ErrorAction SilentlyContinue

& $Python -m PyInstaller --noconfirm --windowed --name "AI News Monitor" `
  --add-data "config.example.yaml;." `
  --add-data ".env.example;." `
  --add-data "START_HERE.md;." `
  --add-data "START_HERE.zh-CN.md;." `
  --add-data "README.md;." `
  --add-data "README.zh-CN.md;." `
  --add-data "LICENSE;." `
  --add-data "docs/project/AI_DISCLOSURE.md;." `
  --add-data "docs/guides/SOURCE_GUIDE.md;." `
  --add-data "docs/guides/NOTIFICATION_GUIDE.md;." `
  --add-data "locales;locales" `
  main.py

New-Item -ItemType Directory -Force release | Out-Null
Copy-Item config.example.yaml, .env.example, START_HERE.md, START_HERE.zh-CN.md, README.md, README.zh-CN.md, LICENSE release/
Copy-Item docs/project/AI_DISCLOSURE.md, docs/guides/SOURCE_GUIDE.md, docs/guides/NOTIFICATION_GUIDE.md release/
Copy-Item -Recurse "dist/AI News Monitor" release/
Compress-Archive -Path "release/*" -DestinationPath "AI-News-Monitor-Windows.zip" -Force
