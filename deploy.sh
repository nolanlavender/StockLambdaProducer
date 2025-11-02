#!/bin/bash

# Stock Lambda Producer Deployment Script

set -e

# Configuration
STACK_NAME="stock-lambda-producer"
REGION="us-east-1"
S3_BUCKET=""  # You'll need to set this to your deployment bucket

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Stock Lambda Producer Deployment${NC}"
echo "================================="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo -e "${RED}SAM CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Prompt for required parameters
if [ -z "$FINNHUB_API_KEY" ]; then
    echo -e "${YELLOW}Enter your Finnhub API Key:${NC}"
    read -s FINNHUB_API_KEY
    if [ -z "$FINNHUB_API_KEY" ]; then
        echo -e "${RED}API Key is required${NC}"
        exit 1
    fi
fi

if [ -z "$S3_BUCKET" ]; then
    echo -e "${YELLOW}Enter your S3 bucket name for deployment artifacts:${NC}"
    read S3_BUCKET
    if [ -z "$S3_BUCKET" ]; then
        echo -e "${RED}S3 bucket is required${NC}"
        exit 1
    fi
fi

# Optional parameters with defaults
KINESIS_STREAM_NAME=${KINESIS_STREAM_NAME:-"stock-prices-stream"}
POLLING_INTERVAL=${POLLING_INTERVAL:-"300"}
ENFORCE_MARKET_HOURS=${ENFORCE_MARKET_HOURS:-"true"}
TEST_MODE=${TEST_MODE:-"false"}

echo -e "${GREEN}Building SAM application...${NC}"
sam build

echo -e "${GREEN}Deploying to AWS...${NC}"
sam deploy \
    --stack-name "$STACK_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --parameter-overrides \
        FinnhubApiKey="$FINNHUB_API_KEY" \
        KinesisStreamName="$KINESIS_STREAM_NAME" \
        PollingIntervalSeconds="$POLLING_INTERVAL" \
        EnforceMarketHours="$ENFORCE_MARKET_HOURS" \
        TestMode="$TEST_MODE" \
    --confirm-changeset

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Stack outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table