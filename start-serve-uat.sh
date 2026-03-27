#!/bin/bash

# Navigate to the working directory
cd /home/admin2/SpecCheckAI-Backend || exit 1

# Activate the virtual environment
source speccheck_ai_be_venv/bin/activate

# Default number of workers for UAT
WORKERS=2

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -w|--workers) WORKERS="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Starting Uvicorn with $WORKERS worker(s) on port 5001..."
uvicorn app:app --host 127.0.0.1 --port 5001 --workers "$WORKERS"
