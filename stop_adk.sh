#!/bin/bash
# =========================================================
# Stop ADK web server + session event watcher
# Usage: ./stop_adk.sh
#   - Kills adk web, fetch_ui_data --watch, and start_adk.sh
#   - Safe to run even if nothing is running
# =========================================================

cd "$(dirname "$0")"

echo "⏹️  Stopping ADK processes..."

# Try graceful SIGTERM first
pkill -f "adk web" 2>/dev/null
pkill -f "fetch_ui_data.py --watch" 2>/dev/null  
pkill -f "start_adk.sh" 2>/dev/null

sleep 1

# Force kill any survivors
if pgrep -f "adk web|fetch_ui_data" > /dev/null 2>&1; then
  echo "⚠️  Force killing remaining processes..."
  pkill -9 -f "adk web" 2>/dev/null
  pkill -9 -f "fetch_ui_data.py --watch" 2>/dev/null
fi

echo "✅ All ADK processes stopped"
