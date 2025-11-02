#!/bin/bash

# API Key Setup Script for Stock Lambda Producer

echo "🔑 Setting up your Finnhub API key..."
echo ""

# Check if API key is provided as argument
if [ -z "$1" ]; then
    echo "Usage: ./set_api_key.sh YOUR_API_KEY_HERE"
    echo ""
    echo "Example: ./set_api_key.sh pk_abc123def456..."
    echo ""
    echo "To get your API key:"
    echo "1. Go to https://finnhub.io/register"
    echo "2. Sign up for free"
    echo "3. Copy your API key from the dashboard"
    echo ""
    exit 1
fi

API_KEY="$1"

# Validate API key format (should start with pk_)
if [[ ! "$API_KEY" =~ ^pk_ ]]; then
    echo "⚠️  Warning: API key should start with 'pk_'"
    echo "Are you sure this is correct? (y/n)"
    read -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 1
    fi
fi

echo "Setting API key for current session..."
export FINNHUB_API_KEY="$API_KEY"

echo "Adding to ~/.zshrc for permanent use..."
# Remove any existing FINNHUB_API_KEY lines
grep -v "FINNHUB_API_KEY" ~/.zshrc > ~/.zshrc.tmp 2>/dev/null || touch ~/.zshrc.tmp
mv ~/.zshrc.tmp ~/.zshrc

# Add the new API key
echo "export FINNHUB_API_KEY=\"$API_KEY\"" >> ~/.zshrc

echo ""
echo "✅ API key set successfully!"
echo ""
echo "Testing the API key..."

# Test the API key
if command -v curl &> /dev/null; then
    response=$(curl -s "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$API_KEY")
    if echo "$response" | grep -q '"c":'; then
        echo "✅ API key is working! Got AAPL price data."
    else
        echo "❌ API key test failed. Response: $response"
    fi
else
    echo "⚠️  curl not found, skipping API test"
fi

echo ""
echo "Next steps:"
echo "1. Source your shell config: source ~/.zshrc"
echo "2. Or restart your terminal"
echo "3. Run the tests: ./test_api.sh"