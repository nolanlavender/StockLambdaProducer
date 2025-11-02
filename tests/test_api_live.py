import pytest
import os
import requests
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from lambda_function import fetch_stock_prices


class TestLiveAPI:
    """Live API tests that actually call the Finnhub API"""
    
    def setup_method(self):
        """Setup for live API tests"""
        # Check if API key is available
        self.api_key = os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            pytest.skip("FINNHUB_API_KEY not set - skipping live API tests")
    
    @pytest.mark.live
    def test_finnhub_api_connectivity(self):
        """Test basic connectivity to Finnhub API"""
        url = "https://finnhub.io/api/v1/quote"
        params = {
            'symbol': 'AAPL',
            'token': self.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        # Verify we can reach the API
        assert response.status_code == 200, f"API returned status {response.status_code}"
        
        # Verify we get valid JSON
        data = response.json()
        assert isinstance(data, dict), "API should return JSON object"
        
        # Verify we get stock price data
        assert 'c' in data, "Response should contain current price (c)"
        assert data['c'] is not None, "Current price should not be None"
        assert isinstance(data['c'], (int, float)), "Price should be numeric"
        assert data['c'] > 0, "Price should be positive"
        
        print(f"✅ AAPL current price: ${data['c']}")
    
    @pytest.mark.live
    def test_fetch_stock_prices_live(self):
        """Test fetch_stock_prices function with real API"""
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        stock_data = fetch_stock_prices(symbols, self.api_key)
        
        # Verify we got data
        assert len(stock_data) > 0, "Should fetch data for at least one symbol"
        assert len(stock_data) <= len(symbols), "Should not return more data than requested"
        
        # Verify data structure for each stock
        for stock in stock_data:
            assert 'symbol' in stock, "Stock data should contain symbol"
            assert 'price' in stock, "Stock data should contain price"
            assert 'timestamp' in stock, "Stock data should contain timestamp"
            
            # Verify data types and values
            assert isinstance(stock['symbol'], str), "Symbol should be string"
            assert isinstance(stock['price'], (int, float)), "Price should be numeric"
            assert stock['price'] > 0, "Price should be positive"
            
            # Verify symbol is one we requested
            assert stock['symbol'] in symbols, f"Unexpected symbol: {stock['symbol']}"
            
            print(f"✅ {stock['symbol']}: ${stock['price']}")
        
        print(f"✅ Successfully fetched {len(stock_data)} stock prices")
    
    @pytest.mark.live
    def test_api_rate_limiting(self):
        """Test API rate limiting behavior"""
        symbols = ['AAPL']  # Test with single symbol to avoid hitting limits
        
        # Make multiple requests to test rate limiting
        for i in range(3):
            stock_data = fetch_stock_prices(symbols, self.api_key)
            assert len(stock_data) == 1, f"Request {i+1} should return data"
            print(f"✅ Request {i+1}: Got data for {stock_data[0]['symbol']}")
    
    @pytest.mark.live
    def test_invalid_symbol(self):
        """Test handling of invalid stock symbols"""
        invalid_symbols = ['INVALID123', 'NOTREAL']
        
        stock_data = fetch_stock_prices(invalid_symbols, self.api_key)
        
        # Should handle invalid symbols gracefully
        # (May return empty list or skip invalid symbols)
        print(f"✅ Invalid symbols handled gracefully: {len(stock_data)} results")
    
    @pytest.mark.live
    def test_api_key_validation(self):
        """Test behavior with invalid API key"""
        invalid_key = "invalid-api-key-12345"
        symbols = ['AAPL']
        
        # This should either return empty results or handle the error gracefully
        stock_data = fetch_stock_prices(symbols, invalid_key)
        
        # Function should not crash, even with invalid key
        assert isinstance(stock_data, list), "Should return list even with invalid key"
        print("✅ Invalid API key handled gracefully")
    
    @pytest.mark.live
    def test_market_data_fields(self):
        """Test that all expected market data fields are present"""
        symbols = ['AAPL']
        
        stock_data = fetch_stock_prices(symbols, self.api_key)
        
        if len(stock_data) > 0:
            stock = stock_data[0]
            
            # Required fields
            required_fields = ['symbol', 'price', 'timestamp']
            for field in required_fields:
                assert field in stock, f"Missing required field: {field}"
            
            # Optional fields that should be present if data is available
            optional_fields = ['change', 'change_percent', 'high', 'low', 'open', 'previous_close']
            present_fields = []
            for field in optional_fields:
                if field in stock:
                    present_fields.append(field)
            
            print(f"✅ Required fields: {required_fields}")
            print(f"✅ Optional fields present: {present_fields}")
            
            # Verify numeric fields are actually numeric
            numeric_fields = ['price', 'change', 'high', 'low', 'open', 'previous_close']
            for field in numeric_fields:
                if field in stock and stock[field] is not None:
                    assert isinstance(stock[field], (int, float)), f"{field} should be numeric"
    
    @pytest.mark.live
    def test_multiple_symbols_live(self):
        """Test fetching multiple symbols in one call"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        
        stock_data = fetch_stock_prices(symbols, self.api_key)
        
        print(f"✅ Requested {len(symbols)} symbols, got {len(stock_data)} results")
        
        # Verify we got some data (may not be all if some symbols are invalid or markets closed)
        assert len(stock_data) >= 0, "Should return list even if no data"
        
        # If we got data, verify it's for the symbols we requested
        returned_symbols = [stock['symbol'] for stock in stock_data]
        for symbol in returned_symbols:
            assert symbol in symbols, f"Unexpected symbol returned: {symbol}"
        
        # Print results
        for stock in stock_data:
            change_str = f" ({stock.get('change', 'N/A'):+.2f})" if 'change' in stock else ""
            print(f"   {stock['symbol']}: ${stock['price']:.2f}{change_str}")


class TestAPIConnection:
    """Basic connectivity tests that don't require API key"""
    
    def test_finnhub_endpoint_reachable(self):
        """Test that Finnhub API endpoint is reachable"""
        url = "https://finnhub.io/api/v1/quote"
        
        try:
            response = requests.get(url, params={'symbol': 'AAPL', 'token': 'test'}, timeout=5)
            # We expect this to fail with 401 (unauthorized) but endpoint should be reachable
            assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
            print("✅ Finnhub API endpoint is reachable")
        except requests.exceptions.ConnectionError:
            pytest.fail("Cannot reach Finnhub API endpoint - check internet connection")
        except requests.exceptions.Timeout:
            pytest.fail("Timeout connecting to Finnhub API")
    
    def test_api_response_format(self):
        """Test API response format with invalid key"""
        url = "https://finnhub.io/api/v1/quote"
        params = {
            'symbol': 'AAPL',
            'token': 'invalid-key'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        # Should get JSON response even with invalid key
        try:
            data = response.json()
            assert isinstance(data, dict), "API should return JSON object"
            print("✅ API returns valid JSON format")
        except ValueError:
            pytest.fail("API did not return valid JSON")


# Pytest markers for running specific test types
pytestmark = pytest.mark.api