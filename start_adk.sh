#!/bin/bash
# =========================================================
# Start ADK web server + session event watcher
# Usage: ./start_adk.sh
#   - Launches adk web with output redirection to adk_debug.log
#   - Launches fetch_ui_data.py in --watch mode
#   - Both run in background; Ctrl+C stops both
# =========================================================

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo " Starting ADK Analytics Department"
echo "=========================================="

# Ensure log directory exists
mkdir -p local_logs

# Clear old logs for a fresh start
> local_logs/adk_debug.log
> local_logs/ui_console_output.log
echo "🧹 Cleared old logs"

# Launch ADK web server with output redirection
.venv/bin/adk web > local_logs/adk_debug.log 2>&1 &
ADK_PID=$!
echo "🚀 ADK web server started (PID: $ADK_PID)"

# Wait briefly for the server to initialize
sleep 2

# Launch the session event watcher
.venv/bin/python local_logs/fetch_ui_data.py --watch &
WATCHER_PID=$!
echo "👀 Session watcher started (PID: $WATCHER_PID)"

echo ""
echo " Access the UI at: http://127.0.0.1:8000"
echo " Log file:         local_logs/adk_debug.log"
echo " Output file:      local_logs/ui_console_output.log"
echo " Press Ctrl+C to stop"
echo "=========================================="

# Trap Ctrl+C to clean up both processes
trap "echo ''; echo '⏹️  Shutting down...'; kill $ADK_PID $WATCHER_PID 2>/dev/null; wait $ADK_PID $WATCHER_PID 2>/dev/null; echo 'Done.'; exit 0" INT TERM

# Wait for either process to exit
wait $ADK_PID $WATCHER_PID 2>/dev/null
