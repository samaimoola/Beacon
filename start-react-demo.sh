#!/bin/bash
# Bash script to start both backend and frontend for macOS/Linux

echo "🌩️ Starting Beacon React Demo..."
echo ""

# Check Python
echo "Checking Python..."
python3 --version || { echo "❌ Python not found"; exit 1; }

# Check Node
echo "Checking Node.js..."
node --version || { echo "❌ Node.js not found"; exit 1; }

echo ""
echo "✅ Prerequisites met"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -q -r requirements.txt

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "🚀 Starting services..."
echo ""

# Start backend in background
echo "Starting backend API on http://localhost:8000..."
python3 api_server.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend on http://localhost:3000..."
cd frontend
npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
