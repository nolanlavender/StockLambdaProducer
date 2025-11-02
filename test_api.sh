#!/bin/bash

# API Testing Script for Stock Lambda Producer
# Tests real connectivity to Finnhub API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Stock Lambda Producer - API Testing${NC}"
echo "===================================="

# Check if API key is set
if [ -z "$FINNHUB_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  FINNHUB_API_KEY not set${NC}"
    echo ""
    echo "To test the real API, set your Finnhub API key:"
    echo "  export FINNHUB_API_KEY=your-api-key-here"
    echo ""
    echo "Or run basic connectivity tests without API key:"
    echo "  python3 -m pytest tests/test_api_live.py::TestAPIConnection -v"
    echo ""
fi

# Check if we're in the right directory
if [ ! -f "lambda_function.py" ]; then
    echo -e "${RED}Error: Please run this script from the StockLambdaProducer directory${NC}"
    exit 1
fi

# Setup virtual environment if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r test_requirements.txt

# Set Python path
export PYTHONPATH="$PWD:$PYTHONPATH"

echo ""
echo -e "${BLUE}Running API tests...${NC}"

# Run connectivity tests (no API key required)
echo -e "${YELLOW}1. Testing basic connectivity...${NC}"
python3 -m pytest tests/test_api_live.py::TestAPIConnection -v --tb=short

# Run live API tests if API key is available
if [ ! -z "$FINNHUB_API_KEY" ]; then
    echo ""
    echo -e "${YELLOW}2. Testing live API with your API key...${NC}"
    python3 -m pytest tests/test_api_live.py::TestLiveAPI -v --tb=short -m live
    
    echo ""
    echo -e "${GREEN}✅ Live API tests completed!${NC}"
    echo -e "${BLUE}Your API key is working and you can fetch real stock data.${NC}"
else
    echo ""
    echo -e "${YELLOW}⏭️  Skipping live API tests (no API key)${NC}"
    echo ""
    echo "To run live API tests:"
    echo "  1. Get a free API key from https://finnhub.io/register"
    echo "  2. Set it: export FINNHUB_API_KEY=your-key-here"
    echo "  3. Run: ./test_api.sh"
fi

echo ""
echo -e "${BLUE}API Test Commands:${NC}"
echo "=================="
echo "# Basic connectivity (no API key needed):"
echo "pytest tests/test_api_live.py::TestAPIConnection -v"
echo ""
echo "# Live API tests (requires API key):"
echo "pytest tests/test_api_live.py::TestLiveAPI -v -m live"
echo ""
echo "# Single API test:"
echo "pytest tests/test_api_live.py::TestLiveAPI::test_finnhub_api_connectivity -v"

# Clean up
unset PYTHONPATH

echo ""
echo -e "${GREEN}🎯 API testing completed!${NC}"