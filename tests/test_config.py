import pytest
import os
import json
from unittest.mock import patch, mock_open, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config import Config


class TestConfig:
    """Test cases for Config class"""
    
    def setup_method(self):
        """Clear environment variables before each test"""
        env_vars = [
            'STOCK_SYMBOLS', 'FINNHUB_API_KEY', 'KINESIS_STREAM_NAME',
            'POLLING_INTERVAL_SECONDS', 'MAX_REQUESTS_PER_MINUTE',
            'AWS_REGION', 'ENFORCE_MARKET_HOURS', 'TEST_MODE',
            'USE_SECRETS_MANAGER', 'SECRET_NAME'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_default_configuration(self):
        """Test default configuration values"""
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                
                assert config.stock_symbols == ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
                assert config.kinesis_stream_name == 'stock-prices-stream'
                assert config.polling_interval_seconds == 300
                assert config.max_requests_per_minute == 60
                assert config.aws_region == 'us-east-1'
                assert config.enforce_market_hours is True
                assert config.test_mode is False
                assert config.use_secrets_manager is True
                assert config.secret_name == 'finnhub-api-key'
                assert config.api_key is None
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        os.environ['STOCK_SYMBOLS'] = 'TSLA,AMZN'
        os.environ['KINESIS_STREAM_NAME'] = 'custom-stream'
        os.environ['POLLING_INTERVAL_SECONDS'] = '60'
        os.environ['TEST_MODE'] = 'true'
        os.environ['USE_SECRETS_MANAGER'] = 'false'
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                
                assert config.stock_symbols == ['TSLA', 'AMZN']
                assert config.kinesis_stream_name == 'custom-stream'
                assert config.polling_interval_seconds == 60
                assert config.test_mode is True
                assert config.use_secrets_manager is False
    
    def test_json_file_configuration(self):
        """Test configuration from JSON file"""
        test_config = {
            'stock_symbols': ['AAPL', 'MSFT'],
            'kinesis_stream_name': 'json-stream',
            'polling_interval_seconds': 120,
            'test_mode': True,
            'use_secrets_manager': False
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
            with patch('os.path.exists', return_value=True):
                config = Config()
                
                assert config.stock_symbols == ['AAPL', 'MSFT']
                assert config.kinesis_stream_name == 'json-stream'
                assert config.polling_interval_seconds == 120
                assert config.test_mode is True
                assert config.use_secrets_manager is False
    
    def test_boolean_string_conversion(self):
        """Test that string boolean values are converted properly"""
        os.environ['ENFORCE_MARKET_HOURS'] = 'false'
        os.environ['TEST_MODE'] = '1'
        os.environ['USE_SECRETS_MANAGER'] = 'yes'
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                
                assert config.enforce_market_hours is False
                assert config.test_mode is True
                assert config.use_secrets_manager is True
    
    def test_stock_symbols_parsing(self):
        """Test that comma-separated stock symbols are parsed correctly"""
        os.environ['STOCK_SYMBOLS'] = ' AAPL , GOOGL , MSFT '
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                
                assert config.stock_symbols == ['AAPL', 'GOOGL', 'MSFT']
    
    @patch('secrets_manager.SecretsManager')
    def test_load_api_key_from_secrets_manager(self, mock_secrets_manager):
        """Test loading API key from Secrets Manager"""
        mock_sm_instance = MagicMock()
        mock_sm_instance.get_api_key.return_value = 'test-api-key'
        mock_secrets_manager.return_value = mock_sm_instance
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                api_key = config.load_api_key()
                
                assert api_key == 'test-api-key'
                assert config.api_key == 'test-api-key'
                mock_secrets_manager.assert_called_once_with(region_name='us-east-1')
                mock_sm_instance.get_api_key.assert_called_once_with(
                    secret_name='finnhub-api-key',
                    fallback_env_var='FINNHUB_API_KEY'
                )
    
    def test_load_api_key_from_env_var(self):
        """Test loading API key from environment variable when Secrets Manager disabled"""
        os.environ['USE_SECRETS_MANAGER'] = 'false'
        os.environ['FINNHUB_API_KEY'] = 'env-api-key'
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                api_key = config.load_api_key()
                
                assert api_key == 'env-api-key'
                assert config.api_key == 'env-api-key'
    
    def test_load_api_key_failure(self):
        """Test that missing API key raises ValueError"""
        os.environ['USE_SECRETS_MANAGER'] = 'false'
        # Don't set FINNHUB_API_KEY
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                
                with pytest.raises(ValueError, match="API key not found"):
                    config.load_api_key()
    
    def test_to_dict(self):
        """Test configuration dictionary representation"""
        os.environ['TEST_MODE'] = 'true'
        
        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('os.path.exists', return_value=True):
                config = Config()
                config.api_key = 'test-key'
                
                config_dict = config.to_dict()
                
                assert 'stock_symbols' in config_dict
                assert 'test_mode' in config_dict
                assert config_dict['test_mode'] is True
                assert config_dict['api_key_configured'] is True
                assert 'secret_name' in config_dict