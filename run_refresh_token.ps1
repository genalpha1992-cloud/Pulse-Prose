# run_refresh_token.ps1
# Wrapper script for Windows Task Scheduler.
# Sets the required environment variables for this run only, then
# executes refresh_token.py. Edit the three values below with your
# real credentials, then point Task Scheduler at this file.

$env:FB_APP_ID = "your_app_id_here"
$env:FB_APP_SECRET = "your_app_secret_here"
$env:IG_ACCESS_TOKEN = "your_current_long_lived_token_here"  # only used the very first run, to bootstrap token_store.json

# Adjust this path to wherever your project folder actually is
Set-Location "C:\Users\shwet\OneDrive\Documents\GitHub\Pulse-Prose"

python refresh_token.py *>> refresh_token_log.txt
