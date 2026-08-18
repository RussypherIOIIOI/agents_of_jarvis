<#
.SYNOPSIS
    Watchdog health-check script for the Insight Agent service.

.DESCRIPTION
    Runs a battery of health checks and writes results to watchdog_state.json.
    Designed to be called on a schedule (e.g. Windows Task Scheduler) to monitor
    the Insight Agent service, detect crash loops, preflight failures, stale
    heartbeats, and missed digest deliveries.

.PARAMETER DryRun
    Print check results to the console without writing state.

.PARAMETER LogTailLines
    Number of lines to read from the service log (default 500).
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [int]$LogTailLines = 500
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Tunables ──────────────────────────────────────────────────────────────────

$HeartbeatMaxAgeSec   = 120          # 2 minutes
$CrashLoopThreshold   = 3           # restarts in the log tail
$DigestMaxAgeSec      = 25 * 3600   # 25 hours

# ── Service identity ──────────────────────────────────────────────────────────

$ServiceName = "InsightAgent"

# ── Paths ─────────────────────────────────────────────────────────────────────

$ProjectRoot       = Split-Path $PSScriptRoot -Parent
$VenvDir           = Join-Path $ProjectRoot ".venv"
$PythonExe         = Join-Path $VenvDir "Scripts" "python.exe"
$HeartbeatFile     = Join-Path $ProjectRoot "heartbeat.txt"
$ServiceLog        = Join-Path $ProjectRoot "logs" "service.log"
$StateFile         = Join-Path $PSScriptRoot "watchdog_state.json"
$DigestCheckScript = Join-Path $PSScriptRoot "check_digest.py"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Get-LogTail {
    param([int]$Lines = 500)
    if (-not (Test-Path $ServiceLog)) { return @() }
    Get-Content $ServiceLog -Tail $Lines -ErrorAction SilentlyContinue
}

# ── Health checks ─────────────────────────────────────────────────────────────

function Test-ServiceRunning {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($null -eq $svc) {
        return @{ ok = $false; detail = "service '$ServiceName' not found" }
    }
    if ($svc.Status -eq 'Running') {
        return @{ ok = $true; detail = "service is running (PID $($svc.ServiceHandle))" }
    }
    return @{ ok = $false; detail = "service status: $($svc.Status)" }
}

function Test-Heartbeat {
    if (-not (Test-Path $HeartbeatFile)) {
        return @{ ok = $false; detail = "heartbeat file not found at $HeartbeatFile" }
    }
    try {
        $raw = (Get-Content $HeartbeatFile -Raw).Trim()
        $lastBeat = [DateTimeOffset]::Parse($raw)
        $age = ([DateTimeOffset]::UtcNow - $lastBeat).TotalSeconds
        if ($age -lt $HeartbeatMaxAgeSec) {
            return @{ ok = $true; detail = "heartbeat ${age}s ago" }
        }
        return @{ ok = $false; detail = "heartbeat stale (${age}s old, threshold ${HeartbeatMaxAgeSec}s)" }
    } catch {
        return @{ ok = $false; detail = "unparseable heartbeat: $raw" }
    }
}

function Test-CrashLoop {
    param([string[]]$Lines)
    $restarts = ($Lines | Select-String -Pattern '(service restarted|fatal|unhandled exception)' -AllMatches).Count
    if ($restarts -ge $CrashLoopThreshold) {
        return @{ ok = $false; detail = "$restarts restart indicators in last $($Lines.Count) log lines" }
    }
    return @{ ok = $true; detail = "$restarts restart indicators (threshold $CrashLoopThreshold)" }
}

function Test-PreflightFailure {
    param([string[]]$Lines)
    $failures = ($Lines | Select-String -Pattern 'preflight.*(fail|error)' -AllMatches).Count
    if ($failures -gt 0) {
        return @{ ok = $false; detail = "$failures preflight failure(s) in last $($Lines.Count) log lines" }
    }
    return @{ ok = $true; detail = "no preflight failures" }
}

function Test-DigestDelivery {
    if (-not (Test-Path $DigestCheckScript)) {
        return @{ ok = $false; detail = "check_digest.py not found at $DigestCheckScript" }
    }
    if (-not (Test-Path $PythonExe)) {
        return @{ ok = $false; detail = "venv python not found at $PythonExe -- venv likely broken" }
    }
    $output = & $PythonExe $DigestCheckScript
    $exitCode = $LASTEXITCODE
    $lastLine = ($output | Select-Object -Last 1)

    if ($exitCode -eq 0) {
        try {
            $lastDigest = [DateTimeOffset]::Parse($lastLine)
            $age = ([DateTimeOffset]::UtcNow - $lastDigest).TotalSeconds
            if ($age -lt (25 * 3600)) {
                $hoursAgo = [int]($age / 3600)
                return @{ ok = $true; detail = "digest delivered ${hoursAgo}h ago" }
            } else {
                return @{ ok = $false; detail = "no successful digest in last 25h (age: $($age)s)" }
            }
        } catch {
            return @{ ok = $false; detail = "unparseable digest timestamp: $lastLine" }
        }
    } elseif ($exitCode -eq 1) {
        return @{ ok = $false; detail = "no successful digest run recorded" }
    } else {
        return @{ ok = $false; detail = "digest query failed (exit $exitCode): $lastLine" }
    }
}

# ── Run checks ────────────────────────────────────────────────────────────────

$logLines = Get-LogTail -Lines $LogTailLines

$checks = [ordered]@{
    service_running   = Test-ServiceRunning
    heartbeat_fresh   = Test-Heartbeat
    no_crash_loop     = Test-CrashLoop -Lines $logLines
    no_preflight_fail = Test-PreflightFailure -Lines $logLines
    digest_delivered  = Test-DigestDelivery
}

# ── Build state ───────────────────────────────────────────────────────────────

$allOk = $true
foreach ($k in $checks.Keys) {
    if (-not $checks[$k].ok) { $allOk = $false }
}

$state = [ordered]@{
    timestamp      = (Get-Date -Format "o")
    healthy        = $allOk
    lastConditions = [ordered]@{}
}

foreach ($k in $checks.Keys) {
    $state.lastConditions[$k] = [ordered]@{
        ok     = $checks[$k].ok
        detail = $checks[$k].detail
    }
}

# ── Output ────────────────────────────────────────────────────────────────────

$json = $state | ConvertTo-Json -Depth 4

if ($DryRun) {
    Write-Host "=== Watchdog DryRun ===" -ForegroundColor Cyan
    Write-Host $json
    Write-Host "=== Overall: $(if ($allOk) { 'HEALTHY' } else { 'UNHEALTHY' }) ===" `
        -ForegroundColor $(if ($allOk) { 'Green' } else { 'Red' })
} else {
    $json | Set-Content -Path $StateFile -Encoding utf8
    Write-Host "Watchdog state written to $StateFile"
    if (-not $allOk) {
        Write-Warning "Watchdog detected unhealthy conditions — see $StateFile"
    }
}

exit $(if ($allOk) { 0 } else { 1 })
