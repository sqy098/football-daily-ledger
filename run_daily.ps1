$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$env:PYTHONUTF8 = '1'
$py = 'C:\Users\velua\.conda\envs\env1\python.exe'
$logDir = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $logDir "daily-$stamp.log"

function Log([string]$m) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

function RunStep([string]$name, [scriptblock]$body) {
    Log "== $name =="
    & $body 2>&1 | ForEach-Object { $line = "$_"; Write-Host $line; Add-Content -Path $log -Value $line -Encoding UTF8 }
    if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}

try {
    Log 'start daily (settle + scan + build + push)'
    RunStep 'daily'  { & $py ledger_daily.py daily }
    RunStep 'build'  { & $py ledger_daily.py build }
    RunStep 'git add' { git add -A }

    $porcelain = (git status --porcelain)
    if ($porcelain) {
        RunStep 'git commit' { git -c user.name=sqy098 -c user.email='32825418+sqy098@users.noreply.github.com' commit -m "daily update $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
        RunStep 'git push'  { git push }
    } else {
        Log 'no changes to commit'
    }
    Log 'done'
} catch {
    Log "FAILED: $($_.Exception.Message)"
    exit 1
}
