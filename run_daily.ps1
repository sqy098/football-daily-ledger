$ErrorActionPreference = 'Stop'
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

try {
    Log 'start daily (settle + scan + build + push)'
    & $py ledger_daily.py daily 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { throw "daily step failed ($LASTEXITCODE)" }

    & $py ledger_daily.py build 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { throw "build step failed ($LASTEXITCODE)" }

    git add -A 2>&1 | Tee-Object -FilePath $log -Append
    $porcelain = (git status --porcelain)
    if ($porcelain) {
        git -c user.name=sqy098 -c user.email='32825418+sqy098@users.noreply.github.com' commit -m "daily update $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>&1 | Tee-Object -FilePath $log -Append
        if ($LASTEXITCODE -ne 0) { throw "git commit failed ($LASTEXITCODE)" }
        git push 2>&1 | Tee-Object -FilePath $log -Append
        if ($LASTEXITCODE -ne 0) { throw "git push failed ($LASTEXITCODE)" }
    } else {
        Log 'no changes to commit'
    }
    Log 'done'
} catch {
    Log "FAILED: $($_.Exception.Message)"
    exit 1
}
