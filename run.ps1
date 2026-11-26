param(
    [ValidateSet('demo', 'check', 'capabilities', 'once', 'run', 'report')]
    [string]$Command = 'demo',
    [string]$Config = 'config.json',
    [string]$State = 'state/paper.sqlite',
    [string]$Output = 'reports/paper'
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $taskPython)) { $taskPython = 'python' }
if ($Command -eq 'capabilities') {
    & $taskPython -m paperlab.capabilities
    exit $LASTEXITCODE
}
& $taskPython -m paperlab $Command --config $Config --state $State --output $Output
exit $LASTEXITCODE
