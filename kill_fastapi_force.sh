#!/bin/bash

# Quick script to immediately kill all FastAPI/uvicorn processes without prompts
echo "💀 Force killing all FastAPI/uvicorn processes..."

# Kill all uvicorn processes
pkill -f "uvicorn" 2>/dev/null

# Kill all Python processes running the FastAPI app
pkill -f "src.api.app:app" 2>/dev/null

# Also kill any Python processes on port 8000 (common FastAPI port)
lsof -ti:8000 | xargs kill -9 2>/dev/null

echo "✅ All FastAPI processes terminated."