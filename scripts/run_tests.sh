#!/bin/bash

# Stock Lambda Producer Test Runner

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Stock Lambda Producer Test Suite${NC}"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "lambda_function.py" ]; then
    echo -e "${RED}Error: Please run this script from the StockLambdaProducer directory${NC}"
    exit 1
fi

# Check if virtual environment exists
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

# Set test environment variables
export PYTHONPATH="$PWD/src:$PWD:$PYTHONPATH"
export CONFIG_FILE_PATH="tests/test_config.json"

# Run different test suites
echo ""
echo -e "${BLUE}Running test suites...${NC}"

# Unit tests
echo -e "${YELLOW}1. Running unit tests...${NC}"
pytest tests/test_config.py -v --tb=short
pytest tests/test_market_hours.py -v --tb=short
pytest tests/test_secrets_manager.py -v --tb=short

# Lambda function tests
echo -e "${YELLOW}2. Running Lambda function tests...${NC}"
pytest tests/test_lambda_function.py -v --tb=short

# Integration tests
echo -e "${YELLOW}3. Running integration tests...${NC}"
pytest tests/test_integration.py -v --tb=short

# Run all tests with coverage
echo -e "${YELLOW}4. Running full test suite with coverage...${NC}"
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html --tb=short

# Generate test report
echo ""
echo -e "${GREEN}Test Summary:${NC}"
echo "=============="
pytest tests/ --tb=no -q

echo ""
echo -e "${GREEN}✅ All tests completed!${NC}"
echo -e "${BLUE}Coverage report generated in htmlcov/index.html${NC}"

# Clean up environment variables
unset PYTHONPATH
unset CONFIG_FILE_PATH

echo -e "${YELLOW}💡 Test Tips:${NC}"
echo "  - Run specific test: pytest tests/test_config.py::TestConfig::test_default_configuration -v"
echo "  - Run with verbose output: pytest tests/ -v"
echo "  - Run only failed tests: pytest tests/ --lf"
echo "  - Run tests matching pattern: pytest tests/ -k 'test_market'"