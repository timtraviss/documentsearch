#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")" || exit 1

# Activate the virtual environment
source venv/bin/activate

# Function to check if server is ready
wait_for_server() {
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost 5000 2>/dev/null; then
            echo "✓ Server is ready!"
            open http://localhost:5000
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 0.5
    done
    
    echo "⚠ Server took longer than expected to start, opening browser anyway..."
    open http://localhost:5000
    return 1
}

# Start server in background and wait for it
python backend/app.py &
SERVER_PID=$!

# Wait for the server to be ready and open browser
wait_for_server

# Keep the script running (so the terminal doesn't close immediately)
wait $SERVER_PID
