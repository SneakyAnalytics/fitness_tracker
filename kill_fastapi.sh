#!/bin/bash

# Script to kill all FastAPI/uvicorn processes
echo "🔍 Searching for FastAPI/uvicorn processes..."

# Find and display running uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn")
PYTHON_FASTAPI_PIDS=$(pgrep -f "src.api.app:app")

if [ -z "$UVICORN_PIDS" ] && [ -z "$PYTHON_FASTAPI_PIDS" ]; then
    echo "✅ No FastAPI/uvicorn processes found running."
    exit 0
fi

echo "📋 Found the following processes:"

# Show uvicorn processes
if [ ! -z "$UVICORN_PIDS" ]; then
    echo "Uvicorn processes:"
    ps -fp $UVICORN_PIDS
fi

# Show Python FastAPI processes
if [ ! -z "$PYTHON_FASTAPI_PIDS" ]; then
    echo "Python FastAPI processes:"
    ps -fp $PYTHON_FASTAPI_PIDS
fi

echo ""
read -p "🔥 Do you want to kill these processes? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "💀 Killing FastAPI/uvicorn processes..."
    
    # Kill uvicorn processes
    if [ ! -z "$UVICORN_PIDS" ]; then
        echo "Killing uvicorn processes: $UVICORN_PIDS"
        kill $UVICORN_PIDS 2>/dev/null
    fi
    
    # Kill Python FastAPI processes
    if [ ! -z "$PYTHON_FASTAPI_PIDS" ]; then
        echo "Killing Python FastAPI processes: $PYTHON_FASTAPI_PIDS"
        kill $PYTHON_FASTAPI_PIDS 2>/dev/null
    fi
    
    # Wait a moment and check if any are still running
    sleep 2
    
    REMAINING_UVICORN=$(pgrep -f "uvicorn")
    REMAINING_FASTAPI=$(pgrep -f "src.api.app:app")
    
    if [ ! -z "$REMAINING_UVICORN" ] || [ ! -z "$REMAINING_FASTAPI" ]; then
        echo "⚠️  Some processes are still running. Force killing..."
        
        if [ ! -z "$REMAINING_UVICORN" ]; then
            kill -9 $REMAINING_UVICORN 2>/dev/null
        fi
        
        if [ ! -z "$REMAINING_FASTAPI" ]; then
            kill -9 $REMAINING_FASTAPI 2>/dev/null
        fi
    fi
    
    echo "✅ All FastAPI/uvicorn processes have been terminated."
else
    echo "❌ Operation cancelled. Processes left running."
fi