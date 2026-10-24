#!/bin/bash
# Development startup script for StormReady React frontend

echo "🌩️ Starting StormReady React Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "⚠️  WARNING: Backend API not detected on port 8000"
    echo "Please start the backend in another terminal:"
    echo "  python api_server.py"
    echo ""
fi

# Start the dev server
echo "🚀 Starting Next.js dev server on http://localhost:3000"
echo ""
npm run dev
