[CmdletBinding()]
param(
    [string]$GodotExecutable = "godot",
    [string]$PythonExecutable = "python",
    [ValidateRange(3, 100)]
    [int]$RunsPerScenario = 3,
    [string]$ResultsDirectory = (Join-Path $PSScriptRoot "results")
)

$ErrorActionPreference = "Stop"
$projectDirectory = $PSScriptRoot
$validatorPath = Join-Path (Split-Path $PSScriptRoot -Parent) "tools\validate_results.py"
$resolvedResultsDirectory = [System.IO.Path]::GetFullPath($ResultsDirectory)
[System.IO.Directory]::CreateDirectory($resolvedResultsDirectory) | Out-Null

$suiteId = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
$resultFiles = [System.Collections.Generic.List[string]]::new()
$scenarios = @("healthy", "node_leak", "cpu_spike")

foreach ($scenario in $scenarios) {
    foreach ($runNumber in 1..$RunsPerScenario) {
        $runId = "{0}-{1}-run-{2:D2}" -f $scenario, $suiteId, $runNumber
        $resultPath = Join-Path $resolvedResultsDirectory "$runId.json"
        Write-Host "Running $scenario ($runNumber/$RunsPerScenario): $runId"
        $godotArguments = @(
            "--headless",
            "--path", $projectDirectory,
            "--",
            "--scenario=$scenario",
            "--run-id=$runId",
            "--output=$resultPath"
        )
        $godotProcess = Start-Process `
            -FilePath $GodotExecutable `
            -ArgumentList $godotArguments `
            -WindowStyle Hidden `
            -Wait `
            -PassThru
        if ($godotProcess.ExitCode -ne 0) {
            throw "Godot exited with code $($godotProcess.ExitCode) while running $runId"
        }
        if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
            throw "Godot reported success but did not create $resultPath"
        }
        $resultFiles.Add($resultPath)
    }
}

Write-Host "Validating $($resultFiles.Count) result files"
& $PythonExecutable $validatorPath @resultFiles
if ($LASTEXITCODE -ne 0) {
    throw "Result validation failed with code $LASTEXITCODE"
}

Write-Host "Benchmark suite passed. Results: $resolvedResultsDirectory"
