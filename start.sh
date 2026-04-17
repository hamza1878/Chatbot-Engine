#!/bin/bash

# Moviroo AI Chatbot - Startup Script
# This script initializes and starts the chatbot backend

set -e

echo "=========================================="
echo "  Moviroo AI Chatbot - Startup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Please update .env with your configuration${NC}"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
    echo ""
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p data models logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
python -c "
from database.connection import init_db
import asyncio
asyncio.run(init_db())
print('✓ Database initialized')
" || echo -e "${RED}⚠️  Database initialization failed. Make sure PostgreSQL is running.${NC}"
echo ""

# Load initial dataset
echo -e "${YELLOW}Loading initial dataset...${NC}"
echo "This will create a sample dataset if dataset.csv doesn't exist."
echo ""

# Ask if user wants to start the server
read -p "Start the server now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "  Starting Moviroo AI Chatbot Server"
    echo "==========================================${NC}"
    echo ""
    echo "API will be available at: http://localhost:8000"
    echo "API Documentation: http://localhost:8000/docs"
    echo ""
    echo "Press CTRL+C to stop the server"
    echo ""
    
    python main.py
else
    echo ""
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo "To start the server, run:"
    echo "  source venv/bin/activate"
    echo "  python main.py"
    echo ""
    echo "Or use Docker:"
    echo "  docker-compose up -d"
    echo ""
fi
