import pytest
import json
import os
from unittest.mock import patch, MagicMock
import responses
from moto import mock_kinesis, mock_secretsmanager
import boto3
from lambda_function import lambda_handler


class TestIntegration:
    """Integration tests for the complete Lambda function"""
    
    @mock_kinesis
    @mock_secretsmanager
    @responses.activate
    def test_end_to_end_with_secrets_manager(self):
        """Test complete end-to-end flow with Secrets Manager"""
        # Setup AWS mocks
        region = 'us-east-1'
        
        # Create Secrets Manager secret
        secrets_client = boto3.client('secretsmanager', region_name=region)
        secret_name = 'test-finnhub-secret'
        api_key = 'test-finnhub-api-key'
        secrets_client.create_secret(
            Name=secret_name,
            SecretString=api_key
        )
        
        # Create Kinesis stream
        kinesis_client = boto3.client('kinesis', region_name=region)
        stream_name = 'test-integration-stream'
        kinesis_client.create_stream(StreamName=stream_name, ShardCount=1)
        
        # Mock Finnhub API responses
        responses.add(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            json={
                'c': 150.25,
                'h': 152.00,
                'l': 149.50,
                'o': 151.00,
                'pc': 147.75
            },
            status=200
        )
        
        # Set environment variables
        os.environ.update({
            'USE_SECRETS_MANAGER': 'true',
            'SECRET_NAME': secret_name,
            'KINESIS_STREAM_NAME': stream_name,
            'TEST_MODE': 'true',
            'STOCK_SYMBOLS': 'AAPL',
            'AWS_REGION': region
        })
        
        # Mock config file
        test_config = {
            'stock_symbols': ['AAPL'],
            'use_secrets_manager': True,
            'secret_name': secret_name,
            'kinesis_stream_name': stream_name,
            'test_mode': True,
            'enforce_market_hours': False
        }
        
        with patch('builtins.open') as mock_open:
            with patch('os.path.exists', return_value=True):
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
                
                # Execute Lambda function
                result = lambda_handler({}, {})
        
        # Verify results
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['records_processed'] == 1
        assert response_body['test_mode'] is True
        
        # Clean up environment
        for var in ['USE_SECRETS_MANAGER', 'SECRET_NAME', 'KINESIS_STREAM_NAME', 
                   'TEST_MODE', 'STOCK_SYMBOLS', 'AWS_REGION']:
            if var in os.environ:
                del os.environ[var]
    
    @responses.activate
    def test_end_to_end_with_env_vars(self, test_environment_vars):
        """Test complete end-to-end flow with environment variables"""
        # Mock Finnhub API response
        responses.add(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            json={
                'c': 175.50,
                'h': 177.00,
                'l': 174.00,
                'o': 176.25,
                'pc': 173.75
            },
            status=200
        )
        
        # Mock Kinesis client
        with patch('lambda_function.kinesis_client') as mock_kinesis:
            mock_kinesis.put_records.return_value = {'FailedRecordCount': 0}
            
            # Mock config file
            test_config = {
                'stock_symbols': ['AAPL'],
                'use_secrets_manager': False,
                'test_mode': True,
                'enforce_market_hours': False
            }
            
            with patch('builtins.open') as mock_open:
                with patch('os.path.exists', return_value=True):
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
                    
                    # Execute Lambda function
                    result = lambda_handler({}, {})
            
            # Verify results
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert response_body['records_processed'] == 1
            assert response_body['test_mode'] is True
            
            # Verify Kinesis was called
            mock_kinesis.put_records.assert_called_once()
            call_args = mock_kinesis.put_records.call_args
            assert call_args[1]['StreamName'] == 'test-kinesis-stream'
            assert len(call_args[1]['Records']) == 1
    
    @responses.activate
    def test_market_hours_enforcement(self, test_environment_vars):
        """Test that market hours enforcement works correctly"""
        # Set to enforce market hours
        os.environ['ENFORCE_MARKET_HOURS'] = 'true'
        os.environ['TEST_MODE'] = 'false'
        
        # Mock config file
        test_config = {
            'stock_symbols': ['AAPL'],
            'use_secrets_manager': False,
            'test_mode': False,
            'enforce_market_hours': True
        }
        
        with patch('builtins.open') as mock_open:
            with patch('os.path.exists', return_value=True):
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
                
                # Mock market hours to be closed
                with patch('market_hours.MarketHours') as mock_market_hours:
                    mock_instance = MagicMock()
                    mock_instance.is_market_open.return_value = (False, "Market closed: Weekend")
                    mock_market_hours.return_value = mock_instance
                    
                    # Execute Lambda function
                    result = lambda_handler({}, {})
        
        # Verify execution was skipped
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert 'Execution skipped' in response_body['message']
        assert response_body['market_status'] == 'closed'
    
    @responses.activate
    def test_api_error_handling(self, test_environment_vars):
        """Test handling of API errors"""
        # Mock Finnhub API to return error
        responses.add(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            status=500
        )
        
        # Mock Kinesis client
        with patch('lambda_function.kinesis_client') as mock_kinesis:
            # Mock config file
            test_config = {
                'stock_symbols': ['AAPL'],
                'use_secrets_manager': False,
                'test_mode': True,
                'enforce_market_hours': False
            }
            
            with patch('builtins.open') as mock_open:
                with patch('os.path.exists', return_value=True):
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
                    
                    # Execute Lambda function
                    result = lambda_handler({}, {})
            
            # Should complete successfully even with API errors
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert response_body['records_processed'] == 0  # No records due to API error
            
            # Kinesis should not be called with no data
            mock_kinesis.put_records.assert_not_called()
    
    @responses.activate
    def test_multiple_symbols(self, test_environment_vars):
        """Test processing multiple stock symbols"""
        # Mock multiple API responses
        def request_callback(request):
            symbol = request.params['symbol']
            if symbol == 'AAPL':
                return (200, {}, json.dumps({
                    'c': 150.0, 'h': 151.0, 'l': 149.0, 'o': 150.5, 'pc': 148.0
                }))
            elif symbol == 'GOOGL':
                return (200, {}, json.dumps({
                    'c': 2500.0, 'h': 2510.0, 'l': 2480.0, 'o': 2495.0, 'pc': 2450.0
                }))
            else:
                return (404, {}, json.dumps({'error': 'Symbol not found'}))
        
        responses.add_callback(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            callback=request_callback
        )
        
        # Update environment for multiple symbols
        os.environ['STOCK_SYMBOLS'] = 'AAPL,GOOGL'
        
        # Mock Kinesis client
        with patch('lambda_function.kinesis_client') as mock_kinesis:
            mock_kinesis.put_records.return_value = {'FailedRecordCount': 0}
            
            # Mock config file
            test_config = {
                'stock_symbols': ['AAPL', 'GOOGL'],
                'use_secrets_manager': False,
                'test_mode': True,
                'enforce_market_hours': False
            }
            
            with patch('builtins.open') as mock_open:
                with patch('os.path.exists', return_value=True):
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_config)
                    
                    # Execute Lambda function
                    result = lambda_handler({}, {})
            
            # Verify results
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert response_body['records_processed'] == 2
            
            # Verify Kinesis was called with correct data
            mock_kinesis.put_records.assert_called_once()
            call_args = mock_kinesis.put_records.call_args
            records = call_args[1]['Records']
            assert len(records) == 2
            
            # Check that both symbols are present
            symbols_sent = []
            for record in records:
                data = json.loads(record['Data'])
                symbols_sent.append(data['symbol'])
            
            assert 'AAPL' in symbols_sent
            assert 'GOOGL' in symbols_sent