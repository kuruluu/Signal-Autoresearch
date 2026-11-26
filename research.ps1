param([ValidateSet('catalog','sources','review','data','pilot','run','report','test','audit','expand','expand-sources','followup','expansion-report','replication-data','replicate-p24','bridge-p24')][string]$Command='report')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $taskPython)) { $taskPython='python' }
$env:PYTHONPATH=(Join-Path $PSScriptRoot '.research-deps')+[IO.Path]::PathSeparator+$PSScriptRoot
$env:PYTHONIOENCODING='utf-8'
switch ($Command) {
    'replication-data' { & $taskPython -m researchlab.p24_data }
    'replicate-p24' { & $taskPython -m researchlab.p24_reproduction }
    'bridge-p24' { & $taskPython -m researchlab.p24_bridge }
    'audit' { & $taskPython -m researchlab.integrity }
    'expand' { & $taskPython -m researchlab.expansion }
    'expand-sources' { & $taskPython -m researchlab.expansion_review --fetch }
    'followup' { & $taskPython -m researchlab.trend_followup }
    'expansion-report' { & $taskPython -m researchlab.expansion_report }
    'pilot' { & $taskPython -m researchlab.experiment --pilot }
    'run' { & $taskPython -m researchlab.experiment }
    'test' { & $taskPython -m unittest discover -s tests -v }
    default { & $taskPython -m "researchlab.$Command" }
}
exit $LASTEXITCODE
