#!/bin/bash

# Stock Lambda Producer Deployment Script

set -e

# Configuration
STACK_NAME="stock-lambda-producer"
REGION="us-east-1"
S3_BUCKET="sam-deployment-staging"  # You'll need to set this to your deployment bucket

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
POLLING_INTERVAL=${POLLING_INTERVAL:-"5"}
ENFORCE_MARKET_HOURS=${ENFORCE_MARKET_HOURS:-"true"}
TEST_MODE=${TEST_MODE:-"false"}
USE_SECRETS_MANAGER=${USE_SECRETS_MANAGER:-"true"}
STOCK_SYMBOLS=${STOCK_SYMBOLS:-"AAPL,GOOGL,MSFT,AMZN,TSLA,META,NVDA,NFLX"}

echo -e "${GREEN}Building SAM application...${NC}"
sam build

echo -e "${GREEN}Deploying to AWS...${NC}"

# Check if stack exists and its status
STACK_INFO=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || echo "false")

if [ "$STACK_INFO" != "false" ]; then
    # Try to get stack status using AWS CLI query (no jq dependency)
    STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "UNKNOWN")
    
    if [ "$STACK_STATUS" = "ROLLBACK_COMPLETE" ]; then
        echo -e "${RED}Stack $STACK_NAME is in ROLLBACK_COMPLETE state${NC}"
        echo -e "${YELLOW}Deleting failed stack before redeployment...${NC}"
        aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
        echo -e "${YELLOW}Waiting for stack deletion to complete...${NC}"
        aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
        echo -e "${GREEN}Stack deleted. Proceeding with fresh deployment...${NC}"
        UPDATE_MODE="--no-confirm-changeset"
    else
        echo -e "${YELLOW}Stack $STACK_NAME already exists (Status: $STACK_STATUS). Updating...${NC}"
        UPDATE_MODE="--no-confirm-changeset"
    fi
else
    echo -e "${YELLOW}Creating new stack $STACK_NAME...${NC}"
    UPDATE_MODE="--no-confirm-changeset"
fi

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
        UseSecretsManager="$USE_SECRETS_MANAGER" \
        StockSymbols="$STOCK_SYMBOLS" \
    $UPDATE_MODE \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo -e "${YELLOW}Stack outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
    
    echo ""
    echo -e "${GREEN}✅ Stack is ready! You can now:${NC}"
    echo -e "${YELLOW}  • Monitor Step Function: AWS Console > Step Functions > $STACK_NAME-stock-price-collector${NC}"
    echo -e "${YELLOW}  • View Kinesis Stream: AWS Console > Kinesis > $KINESIS_STREAM_NAME${NC}"
    echo -e "${YELLOW}  • Check Lambda Logs: AWS Console > CloudWatch > Logs${NC}"
else
    echo -e "${RED}Deployment failed!${NC}"
    echo -e "${YELLOW}Check the error above and run ./scripts/teardown.sh if needed${NC}"
    exit 1
fi