#!/bin/bash

echo "Checking if port 8000 is in use..."
PORT_PROCESS=$(lsof -i :8000 -t)

if [ -n "$PORT_PROCESS" ]; then
    echo "Port 8000 is in use by process(es): $PORT_PROCESS"
    echo "Killing process(es)..."
    kill -9 $PORT_PROCESS
    echo "Process(es) killed."
else
    echo "Port 8000 is not in use."
fi

echo "Starting Flask application on port 8000 with debug mode..."
FLASK_DEBUG=1 python app.py 