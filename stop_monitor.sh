#!/bin/bash
# Stop Portfolio Monitor

if pgrep -f "python3 monitor.py" > /dev/null; then
    pkill -f "python3 monitor.py"
    echo "Monitor stopped."
else
    echo "Monitor is not running."
fi
