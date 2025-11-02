# Stock Lambda Producer

A configurable AWS Lambda function that fetches real-time stock prices and streams them to Amazon Kinesis Data Streams.

## Features

- ✅ Configurable stock symbols and polling intervals
- ✅ Real-time stock price fetching from Finnhub API
- ✅ **Market hours enforcement** - only runs during trading hours
- ✅ **Test mode** - bypass market hours for testing/development
- ✅ **AWS Secrets Manager integration** - secure API key storage
- ✅ Automatic streaming to Kinesis Data Streams
- ✅ Comprehensive error handling and logging
- ✅ Infrastructure as Code with AWS SAM
- ✅ Environment variable and JSON file configuration support

## Architecture

```
EventBridge (12h) → Step Functions → Lambda Function → Finnhub API
                        ↓ (5s loop)        ↓
                    Wait State        Kinesis Data Stream
```

## Directory Structure

```
StockLambdaProducer/
├── src/                        # Source code
│   ├── lambda_function.py      # Main Lambda handler
│   ├── config.py               # Configuration management
│   ├── market_hours.py         # Market hours logic
│   ├── secrets_manager.py      # AWS Secrets Manager integration
│   ├── step_function_controller.py # Step Function controller
│   └── requirements.txt        # Python dependencies
├── scripts/                    # Utility scripts
│   ├── deploy.sh              # Deployment script
│   ├── run_tests.sh           # Test runner
│   ├── test_api.sh            # API connectivity test
│   ├── teardown.sh            # Cleanup script
│   └── local_test.py          # Local testing script
├── configs/                    # Configuration files
│   ├── config.json            # Main configuration
│   └── .env.example           # Environment variables example
├── tests/                      # Test suite
│   ├── test_*.py              # Test files
│   └── test_config.json       # Test configuration
├── template.yaml               # AWS SAM template
├── requirements.txt            # Python dependencies (duplicate for AWS)
├── test_requirements.txt       # Test dependencies
└── README.md                  # This file
```

## Prerequisites

1. **AWS CLI** - [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. **SAM CLI** - [Install Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. **Finnhub API Key** - [Get Free Key](https://finnhub.io/register)
4. **S3 Bucket** for deployment artifacts

## Configuration

The application supports configuration through both environment variables and a JSON config file.

### Environment Variables

- `FINNHUB_API_KEY` - Your Finnhub API key (required)
- `KINESIS_STREAM_NAME` - Name of the Kinesis stream (default: "stock-prices-stream")
- `POLLING_INTERVAL_SECONDS` - How often to fetch prices in seconds (default: 300)
- `STOCK_SYMBOLS` - Comma-separated list of stock symbols (default: "AAPL,GOOGL,MSFT,AMZN,TSLA,META,NVDA,NFLX")
- `ENFORCE_MARKET_HOURS` - Whether to enforce market hours (default: true)
- `TEST_MODE` - Enable test mode to bypass market hours (default: false)
- `USE_SECRETS_MANAGER` - Use AWS Secrets Manager for API key (default: true)
- `SECRET_NAME` - Name of the secret in Secrets Manager (default: "finnhub-api-key")
- `AWS_REGION` - AWS region (default: "us-east-1")

### JSON Configuration File

Edit `configs/config.json` to customize:

```json
{
  "stock_symbols": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
  "kinesis_stream_name": "stock-prices-stream",
  "polling_interval_seconds": 300,
  "max_requests_per_minute": 60,
  "aws_region": "us-east-1",
  "enforce_market_hours": true,
  "test_mode": false,
  "use_secrets_manager": true,
  "secret_name": "finnhub-api-key"
}
```

## 🔐 AWS Secrets Manager Integration

By default, the application uses AWS Secrets Manager to securely store your Finnhub API key. This provides several security benefits:

- **No plaintext API keys** in environment variables or logs
- **Automatic encryption** at rest and in transit
- **IAM-based access control** 
- **Minimal performance impact** (~50ms first call, then cached)

### How It Works

1. **Deployment**: Your API key is stored in Secrets Manager during deployment
2. **Runtime**: Lambda retrieves the key from Secrets Manager on startup
3. **Fallback**: If Secrets Manager fails, falls back to environment variable

### Disabling Secrets Manager

To use environment variables instead (not recommended for production):

```bash
# Deploy without Secrets Manager
USE_SECRETS_MANAGER=false ./scripts/deploy.sh

# Or set in configs/config.json
{
  "use_secrets_manager": false
}
```

## Market Hours Enforcement

By default, the Lambda function only executes during US stock market hours:
- **Trading Days**: Monday-Friday (excluding holidays)
- **Trading Hours**: 9:30 AM - 4:00 PM Eastern Time
- **Holidays**: Major US stock market holidays are automatically detected

### Test Mode

Enable test mode to bypass market hours enforcement for development/testing:

```bash
# Enable test mode via environment variable
export TEST_MODE=true

# Or set in configs/config.json
{
  "test_mode": true
}

# Or deploy with test mode enabled
TEST_MODE=true ./scripts/deploy.sh
```

### Disabling Market Hours Enforcement

```bash
# Disable market hours completely
export ENFORCE_MARKET_HOURS=false

# The function will run regardless of market status
```

## Quick Start

1. **Clone and setup:**
   ```bash
   cd StockLambdaProducer
   ```

2. **Set your API key:**
   ```bash
   export FINNHUB_API_KEY="your-api-key-here"
   ```

3. **Deploy:**
   ```bash
   ./scripts/deploy.sh
   ```

4. **Enable test mode (optional):**
   ```bash
   TEST_MODE=true ./scripts/deploy.sh
   ```

## Manual Deployment

If you prefer manual deployment:

```bash
# Build the application
sam build

# Deploy with parameters
sam deploy \
    --stack-name stock-lambda-producer \
    --s3-bucket your-deployment-bucket \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        FinnhubApiKey="your-api-key" \
        KinesisStreamName="stock-prices-stream" \
        PollingIntervalSeconds="300" \
        EnforceMarketHours="true" \
        TestMode="false" \
        UseSecretsManager="true"
```

## Data Format

Each stock record sent to Kinesis contains:

```json
{
  "symbol": "AAPL",
  "price": 150.25,
  "change": 2.50,
  "change_percent": "1.69",
  "high": 152.00,
  "low": 149.50,
  "open": 151.00,
  "previous_close": 147.75,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Monitoring

- **CloudWatch Logs**: `/aws/lambda/stock-lambda-producer`
- **Kinesis Metrics**: Monitor stream throughput in CloudWatch
- **Lambda Metrics**: Monitor function execution, errors, and duration

## Cost Considerations

- **Finnhub**: Free tier allows 60 API calls per minute
- **Lambda**: Pay per invocation and execution time
- **Kinesis**: Pay per shard hour and PUT payload units
- **CloudWatch**: Pay for log storage and metrics

## Rate Limiting

The free Finnhub API tier has limits:
- 60 API calls per minute
- No daily limit on free tier

The application respects these limits by default. For higher throughput, consider upgrading your Finnhub plan.

## Customization

### Adding More Stock Symbols

Edit `configs/config.json` or set the `STOCK_SYMBOLS` environment variable:

```bash
export STOCK_SYMBOLS="AAPL,GOOGL,MSFT,AMZN,TSLA,META,NVDA,NFLX,JPM,V,WMT,DIS"
```

### Changing Polling Frequency

For more frequent updates (e.g., every 5 seconds):

```bash
export POLLING_INTERVAL_SECONDS=5
```

⚠️ **Warning**: Very frequent polling may exceed API rate limits.

### Custom Kinesis Stream

```bash
export KINESIS_STREAM_NAME="my-custom-stock-stream"
```

## Troubleshooting

### Common Issues

1. **API Rate Limiting**: Reduce polling frequency or upgrade Finnhub plan
2. **Kinesis Throttling**: Increase shard count or reduce data volume
3. **Lambda Timeouts**: Increase timeout in `template.yaml`

### Logs

Check CloudWatch logs for detailed error information:

```bash
aws logs tail /aws/lambda/stock-lambda-producer --follow
```

## 🧪 Local Testing

Before deploying, test your code locally:

### Quick Test
```bash
# Test the Lambda function locally
python3 scripts/local_test.py
```

### Full Test Suite
```bash
# Run comprehensive tests
./scripts/run_tests.sh

# Test real API connectivity
export FINNHUB_API_KEY=your-api-key-here
./scripts/test_api.sh
```

### Test Configuration

The testing framework includes:
- **Unit tests** for individual components
- **Integration tests** for end-to-end flows
- **Live API tests** for real Finnhub connectivity
- **Mock services** for AWS Kinesis and Secrets Manager
- **API response mocking** for Finnhub
- **Market hours testing** with various scenarios

### Test Files Structure
```
tests/
├── __init__.py
├── conftest.py              # Test fixtures and setup
├── test_config.py           # Configuration tests
├── test_market_hours.py     # Market hours logic tests
├── test_secrets_manager.py  # Secrets Manager tests
├── test_lambda_function.py  # Lambda function tests
├── test_integration.py      # End-to-end tests
├── test_api_live.py         # Live API connectivity tests
└── test_config.json         # Test configuration
```

### Running Specific Tests
```bash
# Test only configuration
pytest tests/test_config.py -v

# Test only market hours
pytest tests/test_market_hours.py -v

# Test real API connectivity (requires API key)
pytest tests/test_api_live.py::TestLiveAPI -v -m live

# Test basic connectivity (no API key needed)
pytest tests/test_api_live.py::TestAPIConnection -v

# Test with coverage
pytest tests/ --cov=. --cov-report=html

# Test specific function
pytest tests/test_lambda_function.py::TestLambdaFunction::test_lambda_handler_market_open -v
```

## Security

- API keys are stored as encrypted environment variables
- Lambda function uses least-privilege IAM permissions
- No sensitive data is logged

## License

MIT License - see LICENSE file for details.