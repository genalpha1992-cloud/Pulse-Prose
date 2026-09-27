# run_refresh_token.ps1  (debug version — prints to screen AND logs)

$env:FB_APP_ID = "your_app_id_here"
$env:FB_APP_SECRET = "your_app_secret_here"
$env:IG_ACCESS_TOKEN = "your_current_long_lived_token_here"

$projectPath = "C:\Users\shwet\OneDrive\Documents\GitHub\Pulse-Prose"

Write-Host "Attempting to move to: $projectPath"

try {
    Set-Location -Path $projectPath -ErrorAction Stop
    Write-Host "Successfully moved to: $(Get-Location)"
}
catch {
    Write-Host "FAILED to change directory. Error was:"
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "Checking for python..."
$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    Write-Host "FAILED: python was not found on PATH in this context."
    exit 1
}
Write-Host "Found python at: $($pythonPath.Source)"

Write-Host "Running refresh_token.py..."
python refresh_token.py *>&1 | Tee-Object -FilePath "refresh_token_log.txt"

Write-Host "Done. Check refresh_token_log.txt for the full output."
