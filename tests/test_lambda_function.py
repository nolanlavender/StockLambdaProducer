import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
import boto3
from moto import mock_kinesis
import responses
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from lambda_function import lambda_handler, fetch_stock_prices, send_to_kinesis


class TestLambdaFunction:
    """Test cases for Lambda function"""
    
    @patch('lambda_function.Config')
    @patch('lambda_function.MarketHours')
    def test_lambda_handler_market_closed(self, mock_market_hours, mock_config):
        """Test lambda handler when market is closed"""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.enforce_market_hours = True
        mock_config_instance.test_mode = False
        mock_config_instance.load_api_key.return_value = 'test-key'
        mock_config_instance.to_dict.return_value = {'test': 'config'}
        mock_config.return_value = mock_config_instance
        
        mock_market_hours_instance = MagicMock()
        mock_market_hours_instance.is_market_open.return_value = (False, "Market closed: Weekend")
        mock_market_hours_instance.log_market_status.return_value = None
        mock_market_hours.return_value = mock_market_hours_instance
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert 'Execution skipped' in response_body['message']
        assert response_body['market_status'] == 'closed'
    
    @patch('lambda_function.Config')
    @patch('lambda_function.MarketHours')
    @patch('lambda_function.fetch_stock_prices')
    @patch('lambda_function.send_to_kinesis')
    def test_lambda_handler_market_open(self, mock_send_kinesis, mock_fetch_prices, 
                                       mock_market_hours, mock_config):
        """Test lambda handler when market is open"""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.enforce_market_hours = True
        mock_config_instance.test_mode = False
        mock_config_instance.stock_symbols = ['AAPL', 'GOOGL']
        mock_config_instance.api_key = 'test-key'
        mock_config_instance.kinesis_stream_name = 'test-stream'
        mock_config_instance.load_api_key.return_value = 'test-key'
        mock_config_instance.to_dict.return_value = {'test': 'config'}
        mock_config.return_value = mock_config_instance
        
        mock_market_hours_instance = MagicMock()
        mock_market_hours_instance.is_market_open.return_value = (True, "Market open")
        mock_market_hours.return_value = mock_market_hours_instance
        
        # Mock stock data
        mock_stock_data = [
            {'symbol': 'AAPL', 'price': 150.0},
            {'symbol': 'GOOGL', 'price': 2500.0}
        ]
        mock_fetch_prices.return_value = mock_stock_data
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['records_processed'] == 2
        assert response_body['test_mode'] is False
        mock_fetch_prices.assert_called_once_with(['AAPL', 'GOOGL'], 'test-key')
        mock_send_kinesis.assert_called_once_with(mock_stock_data, 'test-stream')
    
    @patch('lambda_function.Config')
    @patch('lambda_function.MarketHours')
    @patch('lambda_function.fetch_stock_prices')
    def test_lambda_handler_test_mode(self, mock_fetch_prices, mock_market_hours, mock_config):
        """Test lambda handler in test mode (bypasses market hours)"""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.enforce_market_hours = True
        mock_config_instance.test_mode = True
        mock_config_instance.stock_symbols = ['AAPL']
        mock_config_instance.api_key = 'test-key'
        mock_config_instance.kinesis_stream_name = 'test-stream'
        mock_config_instance.load_api_key.return_value = 'test-key'
        mock_config_instance.to_dict.return_value = {'test_mode': True}
        mock_config.return_value = mock_config_instance
        
        mock_market_hours.return_value = MagicMock()
        mock_fetch_prices.return_value = [{'symbol': 'AAPL', 'price': 150.0}]
        
        with patch('lambda_function.send_to_kinesis'):
            result = lambda_handler({}, {})
        
        # Verify test mode bypasses market hours check
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['test_mode'] is True
        # Market hours should not be checked in test mode
        mock_market_hours.return_value.is_market_open.assert_not_called()
    
    @patch('lambda_function.Config')
    def test_lambda_handler_error(self, mock_config):
        """Test lambda handler error handling"""
        # Setup mock to raise exception
        mock_config.side_effect = Exception("Test error")
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify error handling
        assert result['statusCode'] == 500
        response_body = json.loads(result['body'])
        assert 'Test error' in response_body['error']


class TestFetchStockPrices:
    """Test cases for fetch_stock_prices function"""
    
    @responses.activate
    def test_fetch_stock_prices_success(self):
        """Test successful stock price fetching"""
        # Mock Finnhub API response
        responses.add(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            json={
                'c': 150.25,  # current price
                'h': 152.00,  # high
                'l': 149.50,  # low
                'o': 151.00,  # open
                'pc': 147.75  # previous close
            },
            status=200
        )
        
        symbols = ['AAPL']
        api_key = 'test-key'
        
        result = fetch_stock_prices(symbols, api_key)
        
        assert len(result) == 1
        stock_data = result[0]
        assert stock_data['symbol'] == 'AAPL'
        assert stock_data['price'] == 150.25
        assert stock_data['high'] == 152.00
        assert stock_data['low'] == 149.50
        assert stock_data['open'] == 151.00
        assert stock_data['previous_close'] == 147.75
        assert 'timestamp' in stock_data
        
        # Check change calculation
        expected_change = 150.25 - 147.75
        assert stock_data['change'] == expected_change
    
    @responses.activate
    def test_fetch_stock_prices_invalid_response(self):
        """Test handling of invalid API response"""
        # Mock invalid Finnhub API response
        responses.add(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            json={
                'c': None  # Invalid price data
            },
            status=200
        )
        
        symbols = ['INVALID']
        api_key = 'test-key'
        
        result = fetch_stock_prices(symbols, api_key)
        
        assert len(result) == 0  # Should skip invalid data
    
    @responses.activate
    def test_fetch_stock_prices_api_error(self):
        """Test handling of API errors"""
        # Mock API error
        responses.add(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            status=500
        )
        
        symbols = ['AAPL']
        api_key = 'test-key'
        
        result = fetch_stock_prices(symbols, api_key)
        
        assert len(result) == 0  # Should handle errors gracefully
    
    @responses.activate
    def test_fetch_stock_prices_multiple_symbols(self):
        """Test fetching multiple stock symbols"""
        # Mock responses for multiple symbols
        def request_callback(request):
            symbol = request.params['symbol']
            if symbol == 'AAPL':
                return (200, {}, json.dumps({'c': 150.0, 'pc': 145.0, 'h': 151.0, 'l': 149.0, 'o': 150.5}))
            elif symbol == 'GOOGL':
                return (200, {}, json.dumps({'c': 2500.0, 'pc': 2450.0, 'h': 2510.0, 'l': 2480.0, 'o': 2495.0}))
            else:
                return (404, {}, json.dumps({'error': 'Not found'}))
        
        responses.add_callback(
            responses.GET,
            'https://finnhub.io/api/v1/quote',
            callback=request_callback
        )
        
        symbols = ['AAPL', 'GOOGL']
        api_key = 'test-key'
        
        result = fetch_stock_prices(symbols, api_key)
        
        assert len(result) == 2
        assert result[0]['symbol'] == 'AAPL'
        assert result[0]['price'] == 150.0
        assert result[1]['symbol'] == 'GOOGL'
        assert result[1]['price'] == 2500.0


class TestSendToKinesis:
    """Test cases for send_to_kinesis function"""
    
    @mock_kinesis
    def test_send_to_kinesis_success(self):
        """Test successful Kinesis record sending"""
        # Setup Kinesis mock
        kinesis = boto3.client('kinesis', region_name='us-east-1')
        stream_name = 'test-stream'
        kinesis.create_stream(StreamName=stream_name, ShardCount=1)
        
        # Test data
        stock_data = [
            {'symbol': 'AAPL', 'price': 150.0, 'timestamp': '2024-01-01T10:00:00Z'},
            {'symbol': 'GOOGL', 'price': 2500.0, 'timestamp': '2024-01-01T10:00:00Z'}
        ]
        
        # Execute
        with patch('lambda_function.kinesis_client', kinesis):
            send_to_kinesis(stock_data, stream_name)
        
        # Verify records were sent (moto doesn't provide easy verification, but no exception means success)
        # In a real test, you might check CloudWatch metrics or use a different approach
    
    @mock_kinesis
    def test_send_to_kinesis_empty_data(self):
        """Test sending empty data to Kinesis"""
        # Setup Kinesis mock
        kinesis = boto3.client('kinesis', region_name='us-east-1')
        stream_name = 'test-stream'
        kinesis.create_stream(StreamName=stream_name, ShardCount=1)
        
        # Execute with empty data
        with patch('lambda_function.kinesis_client', kinesis):
            send_to_kinesis([], stream_name)
        
        # Should complete without error
    
    def test_send_to_kinesis_client_error(self):
        """Test Kinesis client error handling"""
        # Mock Kinesis client that raises an error
        mock_kinesis_client = MagicMock()
        mock_kinesis_client.put_records.side_effect = Exception("Kinesis error")
        
        stock_data = [{'symbol': 'AAPL', 'price': 150.0}]
        
        with patch('lambda_function.kinesis_client', mock_kinesis_client):
            with pytest.raises(Exception, match="Kinesis error"):
                send_to_kinesis(stock_data, 'test-stream')
    
    def test_send_to_kinesis_record_format(self):
        """Test that records are formatted correctly for Kinesis"""
        mock_kinesis_client = MagicMock()
        mock_kinesis_client.put_records.return_value = {'FailedRecordCount': 0}
        
        stock_data = [
            {'symbol': 'AAPL', 'price': 150.0, 'timestamp': '2024-01-01T10:00:00Z'}
        ]
        
        with patch('lambda_function.kinesis_client', mock_kinesis_client):
            send_to_kinesis(stock_data, 'test-stream')
        
        # Verify the call was made with correct format
        mock_kinesis_client.put_records.assert_called_once()
        call_args = mock_kinesis_client.put_records.call_args
        
        assert call_args[1]['StreamName'] == 'test-stream'
        records = call_args[1]['Records']
        assert len(records) == 1
        
        record = records[0]
        assert record['PartitionKey'] == 'AAPL'
        assert isinstance(record['Data'], str)
        
        # Verify the data can be parsed back to JSON
        parsed_data = json.loads(record['Data'])
        assert parsed_data['symbol'] == 'AAPL'
        assert parsed_data['price'] == 150.0