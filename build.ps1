<#
Builds the bot map database (ootmap\) from your own Ocarina of Time ROM.

  .\build.ps1 -Rom "C:\path\to\Zelda no Densetsu - Toki no Ocarina (Japan).z64"

Needs git and Python 3. The ROM must be NTSC-J 1.0 (MD5 9f04c8e68534b870f707c247fa4b50fc).
#>
param([Parameter(Mandatory = $true)][string]$Rom)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$ref = Join-Path $root "ref"

$md5 = (Get-FileHash -LiteralPath $Rom -Algorithm MD5).Hash.ToLower()
if ($md5 -ne "9f04c8e68534b870f707c247fa4b50fc") {
    throw "This ROM's MD5 is $md5. Expected 9f04c8e68534b870f707c247fa4b50fc (Ocarina of Time NTSC-J 1.0)."
}

# Reference sources, pinned to the exact commits this database was built and checked against.
$refs = @(
    @{ Dir = "oot";  Url = "https://github.com/zeldaret/oot.git";                 Commit = "2c78bc78fd7db383c5f81a83a5169e8de9eb3a0d" },
    @{ Dir = "ootr"; Url = "https://github.com/OoTRandomizer/OoT-Randomizer.git"; Commit = "d262f7a506d8059e538a899ae0dd7d18d3987a6f" }
)
New-Item -ItemType Directory -Force $ref | Out-Null
foreach ($r in $refs) {
    $d = Join-Path $ref $r.Dir
    if (-not (Test-Path (Join-Path $d ".git"))) {
        git init -q $d
        git -C $d config core.longpaths true
        git -C $d remote add origin $r.Url
    }
    $have = (git -C $d rev-parse --verify -q HEAD) 2>$null
    if ($have -ne $r.Commit) {
        Write-Host "Fetching $($r.Url) @ $($r.Commit.Substring(0, 10))..."
        git -C $d fetch -q --depth 1 origin $r.Commit
        git -C $d checkout -q -f $r.Commit
    }
}

$tools = Join-Path $root "tools"
$out = Join-Path $root "ootmap"
Write-Host "1/3 Reading the ROM..."
python -I (Join-Path $tools "extract_map.py") $tools (Join-Path $ref "oot") $Rom $out | Out-File -Encoding utf8 (Join-Path $root "extract.log")
if ($LASTEXITCODE -ne 0) { throw "extract_map.py failed (see extract.log)" }
Write-Host "2/3 Indexing decomp functions..."
python -I (Join-Path $tools "scan_source.py") $tools (Join-Path $ref "oot") (Join-Path $out "code")
if ($LASTEXITCODE -ne 0) { throw "scan_source.py failed" }
Write-Host "3/3 Joining logic, items and warps..."
python -I (Join-Path $tools "build_bot_db.py") $tools (Join-Path $ref "oot") (Join-Path $ref "ootr") $out
if ($LASTEXITCODE -ne 0) { throw "build_bot_db.py failed" }
Write-Host "Done. Start with ootmap\HOW_TO_USE.md"
