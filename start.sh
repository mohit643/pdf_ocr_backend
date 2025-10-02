#!/bin/bash

# PDF Editor - Quick Start Script
# Save as: start.sh
# Make executable: chmod +x start.sh

echo "================================================"
echo "🚀 PDF Editor - Quick Start"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PostgreSQL is installed
echo "📦 Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL found${NC}"
else
    echo -e "${RED}❌ PostgreSQL not found${NC}"
    echo "Install with: sudo apt install postgresql (Ubuntu/Debian)"
    echo "Or: brew install postgresql (macOS)"
    exit 1
fi

# Check if database exists
echo ""
echo "================================================"
echo -e "${GREEN}✅ PDF Editor is running!${NC}"
echo "================================================"
echo ""
echo "📱 Access Points:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 To stop servers:"
echo "   Press Ctrl+C or run: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "📊 Monitor logs in terminal"
echo "================================================"

# Keep script running
wait "🔍 Checking database..."
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw pdf_editor; then
    echo -e "${GREEN}✅ Database 'pdf_editor' exists${NC}"
else
    echo -e "${YELLOW}⚠️  Database 'pdf_editor' not found${NC}"
    echo "Creating database..."
    sudo -u postgres psql -c "CREATE DATABASE pdf_editor;"
    echo -e "${GREEN}✅ Database created${NC}"
fi

# Backend setup
echo ""
echo "🐍 Setting up Backend..."
cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env file..."
    cat > .env << EOF
DATABASE_URL=postgresql://postgres:password@localhost:5432/pdf_editor
REDIS_HOST=localhost
REDIS_PORT=6379
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
THUMBNAIL_DIR=thumbnails
SECRET_KEY=$(openssl rand -hex 32)
HOST=0.0.0.0
PORT=8000
EOF
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please update DATABASE_URL with your PostgreSQL password${NC}"
fi

# Initialize database
echo ""
echo "💾 Initializing database..."
python -c "from database import init_db; init_db()" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database initialized${NC}"
else
    echo -e "${YELLOW}⚠️  Database initialization skipped (may already exist)${NC}"
fi

# Start backend
echo ""
echo "🚀 Starting Backend Server..."
echo "================================================"
python app.py &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend running on http://localhost:8000${NC}"
echo "   API Docs: http://localhost:8000/docs"
echo "   PID: $BACKEND_PID"

# Wait a bit for backend to start
sleep 3

# Frontend setup (if exists)
cd ..
if [ -d "frontend" ]; then
    echo ""
    echo "⚛️  Starting Frontend..."
    cd frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install -q
        echo -e "${GREEN}✅ Dependencies installed${NC}"
    fi
    
    echo "🚀 Starting Frontend Server..."
    npm start &
    FRONTEND_PID=$!
    echo -e "${GREEN}✅ Frontend running on http://localhost:3000${NC}"
    echo "   PID: $FRONTEND_PID"
else
    echo -e "${YELLOW}⚠️  Frontend folder not found${NC}"
fi

echo ""
echo