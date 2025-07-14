#!/bin/bash

# Name of the Python script
SCRIPT_NAME="scripts.workers.submission_worker"
SCREEN_NAME="worker"

cd /home/evalai

# Function to check if the script is running
is_script_running() {
    pgrep -f "$SCRIPT_NAME" >/dev/null
}

if ! is_script_running; then
    echo "Script is not running. Restarting..."
    /home/evalai/venv/bin/python -m $SCRIPT_NAME >> /var/log/worker.log
else
    echo "Script is running."
fi
