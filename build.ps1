<#
Builds the bot map database (ootmap\) from your own Ocarina of Time ROM. Needs only Python 3.

  .\build.ps1 -Rom "C:\path\to\Zelda no Densetsu - Toki no Ocarina (Japan).z64"

(Same as: python -I tools\build.py --rom "<path>")
#>
param([Parameter(Mandatory = $true)][string]$Rom)

$ErrorActionPreference = "Stop"
python -I (Join-Path $PSScriptRoot "tools\build.py") --rom $Rom
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
