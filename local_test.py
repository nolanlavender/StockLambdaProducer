#!/usr/bin/env python3
"""
Local testing script for Stock Lambda Producer
Allows testing the Lambda function locally without deploying to AWS
"""

import os
import sys
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_function import lambda_handler


def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        'FINNHUB_API_KEY': 'your-test-api-key-here',  # Replace with your actual API key
        'KINESIS_STREAM_NAME': 'local-test-stream',
        'STOCK_SYMBOLS': 'AAPL,GOOGL,MSFT',
        'TEST_MODE': 'true',
        'USE_SECRETS_MANAGER': 'false',
        'ENFORCE_MARKET_HOURS': 'false',
        'POLLING_INTERVAL_SECONDS': '60',
        'AWS_REGION': 'us-east-1'
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    return test_env


def mock_kinesis_client():
    """Mock Kinesis client for local testing"""
    mock_client = MagicMock()
    mock_client.put_records.return_value = {
        'FailedRecordCount': 0,
        'Records': [
            {'SequenceNumber': '123', 'ShardId': 'shardId-000000000000'}
        ]
    }
    return mock_client


def test_lambda_locally():
    """Test the Lambda function locally"""
    print("🚀 Starting local Lambda test...")
    print("=" * 50)
    
    # Setup environment
    env_vars = setup_test_environment()
    print("✅ Environment variables set:")
    for key, value in env_vars.items():
        if 'API_KEY' in key:
            print(f"   {key}: {'*' * len(value)}")  # Hide API key
        else:
            print(f"   {key}: {value}")
    
    # Mock Kinesis to avoid AWS calls
    with patch('lambda_function.kinesis_client', mock_kinesis_client()):
        print("\n🧪 Testing Lambda function...")
        
        # Test event and context
        test_event = {}
        test_context = type('Context', (), {
            'function_name': 'local-test',
            'memory_limit_in_mb': 256,
            'remaining_time_in_millis': lambda: 30000
        })()
        
        try:
            # Execute Lambda function
            result = lambda_handler(test_event, test_context)
            
            print("\n📊 Lambda Function Result:")
            print("-" * 30)
            print(f"Status Code: {result['statusCode']}")
            
            body = json.loads(result['body'])
            print(f"Message: {body.get('message', 'N/A')}")
            print(f"Records Processed: {body.get('records_processed', 0)}")
            print(f"Test Mode: {body.get('test_mode', False)}")
            print(f"Timestamp: {body.get('timestamp', 'N/A')}")
            
            if result['statusCode'] == 200:
                print("\n✅ Lambda function executed successfully!")
                if body.get('records_processed', 0) > 0:
                    print(f"   📈 Processed {body['records_processed']} stock records")
                else:
                    print("   ⚠️  No stock records processed (check API key or network)")
            else:
                print(f"\n❌ Lambda function failed with status {result['statusCode']}")
                if 'error' in body:
                    print(f"   Error: {body['error']}")
                    
        except Exception as e:
            print(f"\n💥 Exception occurred: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🏁 Local test completed!")


def test_market_hours():
    """Test market hours functionality"""
    print("\n🕐 Testing market hours functionality...")
    
    from market_hours import MarketHours
    
    market_hours = MarketHours()
    is_open, reason = market_hours.is_market_open()
    
    print(f"Current market status: {'OPEN' if is_open else 'CLOSED'}")
    print(f"Reason: {reason}")
    
    if not is_open:
        next_open = market_hours.get_next_market_open()
        print(f"Next market open: {next_open.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def test_config_loading():
    """Test configuration loading"""
    print("\n⚙️  Testing configuration loading...")
    
    from config import Config
    
    try:
        config = Config()
        print("✅ Configuration loaded successfully")
        print(f"   Stock symbols: {config.stock_symbols}")
        print(f"   Kinesis stream: {config.kinesis_stream_name}")
        print(f"   Test mode: {config.test_mode}")
        print(f"   Market hours enforcement: {config.enforce_market_hours}")
        print(f"   Using Secrets Manager: {config.use_secrets_manager}")
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")


def main():
    """Main function"""
    print("🧪 Stock Lambda Producer - Local Testing")
    print("=" * 50)
    
    # Test configuration loading
    test_config_loading()
    
    # Test market hours
    test_market_hours()
    
    # Test Lambda function
    test_lambda_locally()
    
    print("\n💡 Next steps:")
    print("   1. Replace 'your-test-api-key-here' with your actual Finnhub API key")
    print("   2. Run the full test suite: ./run_tests.sh")
    print("   3. Deploy to AWS: ./deploy.sh")


if __name__ == "__main__":
    main()