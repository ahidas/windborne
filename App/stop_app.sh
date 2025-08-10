#!/bin/bash
echo "🛑 Stopping Windborne Satellite Network Analyzer..."

# Kill processes from .env if it exists
if [ -f ".env" ]; then
    source .env
    kill $FLASK_PID $NGROK_PID 2>/dev/null || true
fi

# Fallback: kill by process name
pkill -f "python app.py" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true

echo "✅ Stopped successfully"
