#!/bin/bash

# Stock Lambda Producer Teardown Script
# Safely removes all AWS resources created by the deployment

set -e

# Configuration (should match deploy.sh)
STACK_NAME="stock-lambda-producer"
REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}Stock Lambda Producer Teardown${NC}"
echo "================================="
echo -e "${YELLOW}⚠️  This will DELETE all resources created by the deployment:${NC}"
echo "   - Lambda function"
echo "   - Kinesis Data Stream"
echo "   - Secrets Manager secret"
echo "   - CloudWatch Log Groups"
echo "   - EventBridge schedule"
echo "   - IAM roles and policies"
echo ""

# Confirmation prompt
echo -e "${YELLOW}Are you sure you want to proceed? (y/N):${NC}"
read -r confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Teardown cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Starting teardown process...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if stack exists
echo -e "${YELLOW}Checking if stack exists...${NC}"
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &>/dev/null; then
    echo -e "${YELLOW}Stack '$STACK_NAME' not found. Nothing to delete.${NC}"
    exit 0
fi

# Get stack resources before deletion for verification
echo -e "${YELLOW}Getting current stack resources...${NC}"
aws cloudformation list-stack-resources \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'StackResourceSummaries[*].[ResourceType,LogicalResourceId,PhysicalResourceId]' \
    --output table

echo ""
echo -e "${YELLOW}Deleting CloudFormation stack...${NC}"

# Delete the stack
aws cloudformation delete-stack \
    --stack-name "$STACK_NAME" \
    --region "$REGION"

echo -e "${YELLOW}Stack deletion initiated. Waiting for completion...${NC}"
echo "This may take a few minutes..."

# Wait for stack deletion to complete
aws cloudformation wait stack-delete-complete \
    --stack-name "$STACK_NAME" \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Stack deleted successfully!${NC}"
else
    echo -e "${RED}❌ Stack deletion may have failed. Check AWS Console for details.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Checking for any remaining resources...${NC}"

# Check if any resources still exist (shouldn't happen with successful deletion)
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Stack still exists. Check AWS Console for any issues.${NC}"
else
    echo -e "${GREEN}✅ Stack completely removed.${NC}"
fi

echo ""
echo -e "${BLUE}Optional cleanup tasks:${NC}"
echo "======================"

# Optional: Clean up S3 deployment artifacts
echo -e "${YELLOW}Clean up S3 deployment artifacts? (y/N):${NC}"
read -r cleanup_s3

if [[ "$cleanup_s3" =~ ^[Yy]$ ]]; then
    if [ ! -z "$S3_BUCKET" ]; then
        echo -e "${YELLOW}Listing deployment artifacts in S3...${NC}"
        aws s3 ls s3://$S3_BUCKET/ --recursive | grep stock-lambda || echo "No artifacts found"
        
        echo -e "${YELLOW}Delete S3 artifacts? (y/N):${NC}"
        read -r delete_s3
        
        if [[ "$delete_s3" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Deleting S3 artifacts...${NC}"
            aws s3 rm s3://$S3_BUCKET/ --recursive --exclude "*" --include "*stock-lambda*" || echo "No artifacts to delete"
            echo -e "${GREEN}✅ S3 artifacts cleaned up.${NC}"
        fi
    else
        echo -e "${YELLOW}S3_BUCKET not set. Skipping S3 cleanup.${NC}"
    fi
fi

# Optional: Remove local build artifacts
echo ""
echo -e "${YELLOW}Clean up local build artifacts? (y/N):${NC}"
read -r cleanup_local

if [[ "$cleanup_local" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Removing local build artifacts...${NC}"
    rm -rf .aws-sam/
    rm -rf __pycache__/
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    echo -e "${GREEN}✅ Local artifacts cleaned up.${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Teardown completed!${NC}"
echo ""
echo -e "${BLUE}Summary of what was removed:${NC}"
echo "  ✅ Lambda function and execution role"
echo "  ✅ Kinesis Data Stream"
echo "  ✅ Secrets Manager secret (if created)"
echo "  ✅ EventBridge schedule"
echo "  ✅ CloudWatch Log Groups"
echo "  ✅ All associated IAM roles and policies"
echo ""
echo -e "${YELLOW}💡 To redeploy, run: ./deploy.sh${NC}"