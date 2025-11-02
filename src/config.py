import os
import json
from typing import List, Optional
from secrets_manager import SecretsManager

class Config:
    """
    Configuration class for the Stock Lambda Producer
    Supports both environment variables and JSON configuration file
    """
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables or config file"""
        
        # Try to load from config file first
        config_file_path = os.getenv('CONFIG_FILE_PATH', 'configs/config.json')
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r') as f:
                file_config = json.load(f)
        else:
            file_config = {}
        
        # Stock symbols to track
        self.stock_symbols = self._get_config_value(
            'STOCK_SYMBOLS', 
            file_config.get('stock_symbols', []),
            default=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
        )
        
        # API configuration - support both Secrets Manager and direct env var
        self.use_secrets_manager = self._get_config_value(
            'USE_SECRETS_MANAGER',
            file_config.get('use_secrets_manager'),
            default=True
        )
        
        # Convert string 'true'/'false' to boolean
        if isinstance(self.use_secrets_manager, str):
            self.use_secrets_manager = self.use_secrets_manager.lower() in ('true', '1', 'yes', 'on')
        
        self.secret_name = self._get_config_value(
            'SECRET_NAME',
            file_config.get('secret_name'),
            default='finnhub-api-key'
        )
        
        # This will be populated later by the secrets manager or env var
        self.api_key = None
        
        # Kinesis stream configuration
        self.kinesis_stream_name = self._get_config_value(
            'KINESIS_STREAM_NAME',
            file_config.get('kinesis_stream_name'),
            default='stock-prices-stream'
        )
        
        # Polling interval (in seconds) - used for EventBridge scheduling
        self.polling_interval_seconds = int(self._get_config_value(
            'POLLING_INTERVAL_SECONDS',
            file_config.get('polling_interval_seconds'),
            default=300  # 5 minutes default
        ))
        
        # API rate limiting
        self.max_requests_per_minute = int(self._get_config_value(
            'MAX_REQUESTS_PER_MINUTE',
            file_config.get('max_requests_per_minute'),
            default=60  # Finnhub free tier limit
        ))
        
        # AWS region
        self.aws_region = self._get_config_value(
            'AWS_REGION',
            file_config.get('aws_region'),
            default='us-east-1'
        )
        
        # Market hours enforcement
        self.enforce_market_hours = self._get_config_value(
            'ENFORCE_MARKET_HOURS',
            file_config.get('enforce_market_hours'),
            default=True
        )
        
        # Convert string 'true'/'false' to boolean
        if isinstance(self.enforce_market_hours, str):
            self.enforce_market_hours = self.enforce_market_hours.lower() in ('true', '1', 'yes', 'on')
        
        # Test mode - bypasses market hours check
        self.test_mode = self._get_config_value(
            'TEST_MODE',
            file_config.get('test_mode'),
            default=False
        )
        
        # Convert string 'true'/'false' to boolean
        if isinstance(self.test_mode, str):
            self.test_mode = self.test_mode.lower() in ('true', '1', 'yes', 'on')
    
    def load_api_key(self) -> Optional[str]:
        """
        Load API key from Secrets Manager or environment variable
        
        Returns:
            The API key or None if not found
        """
        if self.use_secrets_manager:
            try:
                secrets_manager = SecretsManager(region_name=self.aws_region)
                self.api_key = secrets_manager.get_api_key(
                    secret_name=self.secret_name,
                    fallback_env_var='FINNHUB_API_KEY'
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to initialize Secrets Manager: {e}")
                # Fallback to environment variable
                self.api_key = os.getenv('FINNHUB_API_KEY')
        else:
            # Use environment variable directly
            self.api_key = os.getenv('FINNHUB_API_KEY')
        
        if not self.api_key:
            raise ValueError("API key not found in Secrets Manager or environment variables")
        
        return self.api_key
    
    def _get_config_value(self, env_var: str, file_value, default=None, required=False):
        """Get configuration value with priority: env var > file > default"""
        value = os.getenv(env_var, file_value if file_value is not None else default)
        
        if required and value is None:
            raise ValueError(f"Required configuration {env_var} is not set")
        
        # Handle comma-separated lists in environment variables
        if env_var == 'STOCK_SYMBOLS' and isinstance(value, str):
            value = [symbol.strip().upper() for symbol in value.split(',')]
        
        return value
    
    def to_dict(self) -> dict:
        """Return configuration as dictionary for logging/debugging"""
        return {
            'stock_symbols': self.stock_symbols,
            'kinesis_stream_name': self.kinesis_stream_name,
            'polling_interval_seconds': self.polling_interval_seconds,
            'max_requests_per_minute': self.max_requests_per_minute,
            'aws_region': self.aws_region,
            'enforce_market_hours': self.enforce_market_hours,
            'test_mode': self.test_mode,
            'use_secrets_manager': self.use_secrets_manager,
            'secret_name': self.secret_name if self.use_secrets_manager else 'N/A',
            'api_key_configured': bool(self.api_key)
        }