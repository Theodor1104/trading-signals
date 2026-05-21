#!/bin/bash
# Start Portfolio Monitor in background
# Monitors your holdings and sends SMS alerts on SELL signals

cd "$(dirname "$0")"

# Check if already running
if pgrep -f "python3 monitor.py" > /dev/null; then
    echo "Monitor is already running!"
    echo "To stop: ./stop_monitor.sh"
    exit 1
fi

# Start in background
echo "Starting Portfolio Monitor..."
nohup python3 monitor.py > monitor.log 2>&1 &

sleep 2

if pgrep -f "python3 monitor.py" > /dev/null; then
    echo "Monitor started successfully!"
    echo ""
    echo "View logs: tail -f monitor.log"
    echo "Stop:      ./stop_monitor.sh"
else
    echo "Failed to start monitor. Check monitor.log for errors."
fi
