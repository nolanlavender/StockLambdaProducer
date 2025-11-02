import pytest
import os
import json
from unittest.mock import patch


@pytest.fixture
def clean_environment():
    """Fixture to clean environment variables before each test"""
    env_vars_to_clean = [
        'STOCK_SYMBOLS', 'FINNHUB_API_KEY', 'KINESIS_STREAM_NAME',
        'POLLING_INTERVAL_SECONDS', 'MAX_REQUESTS_PER_MINUTE',
        'AWS_REGION', 'ENFORCE_MARKET_HOURS', 'TEST_MODE',
        'USE_SECRETS_MANAGER', 'SECRET_NAME', 'CONFIG_FILE_PATH'
    ]
    
    # Store original values
    original_values = {}
    for var in env_vars_to_clean:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        os.environ[var] = value


@pytest.fixture
def test_config():
    """Fixture providing test configuration data"""
    return {
        'stock_symbols': ['AAPL', 'GOOGL', 'MSFT'],
        'kinesis_stream_name': 'test-stream',
        'polling_interval_seconds': 60,
        'max_requests_per_minute': 30,
        'aws_region': 'us-east-1',
        'enforce_market_hours': False,
        'test_mode': True,
        'use_secrets_manager': False,
        'secret_name': 'test-secret'
    }


@pytest.fixture
def mock_config_file(test_config):
    """Fixture to mock configuration file reading"""
    with patch('builtins.open', create=True) as mock_open:
        with patch('os.path.exists', return_value=True) as mock_exists:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
            yield mock_open


@pytest.fixture
def sample_stock_data():
    """Fixture providing sample stock price data"""
    return [
        {
            'symbol': 'AAPL',
            'price': 150.25,
            'change': 2.50,
            'change_percent': '1.69',
            'high': 152.00,
            'low': 149.50,
            'open': 151.00,
            'previous_close': 147.75,
            'timestamp': '2024-01-15T10:30:00.000Z'
        },
        {
            'symbol': 'GOOGL',
            'price': 2500.00,
            'change': -15.25,
            'change_percent': '-0.61',
            'high': 2520.00,
            'low': 2495.00,
            'open': 2510.00,
            'previous_close': 2515.25,
            'timestamp': '2024-01-15T10:30:00.000Z'
        }
    ]


@pytest.fixture
def mock_finnhub_response():
    """Fixture providing mock Finnhub API response"""
    return {
        'c': 150.25,  # current price
        'h': 152.00,  # high
        'l': 149.50,  # low
        'o': 151.00,  # open
        'pc': 147.75  # previous close
    }


@pytest.fixture
def test_environment_vars():
    """Fixture to set test environment variables"""
    test_vars = {
        'FINNHUB_API_KEY': 'test-api-key',
        'KINESIS_STREAM_NAME': 'test-kinesis-stream',
        'TEST_MODE': 'true',
        'USE_SECRETS_MANAGER': 'false',
        'ENFORCE_MARKET_HOURS': 'false'
    }
    
    # Set test environment variables
    for var, value in test_vars.items():
        os.environ[var] = value
    
    yield test_vars
    
    # Clean up
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture
def lambda_context():
    """Fixture providing mock Lambda context"""
    class MockContext:
        def __init__(self):
            self.function_name = 'test-function'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
            self.memory_limit_in_mb = 256
            self.remaining_time_in_millis = lambda: 30000
            self.log_group_name = '/aws/lambda/test-function'
            self.log_stream_name = '2024/01/15/[$LATEST]test123'
            self.aws_request_id = 'test-request-id'
    
    return MockContext()