import pytest
import json
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from secrets_manager import SecretsManager


class TestSecretsManager:
    """Test cases for SecretsManager class"""
    
    def setup_method(self):
        """Setup test instance"""
        with patch('boto3.client'):
            self.secrets_manager = SecretsManager('us-east-1')
    
    def test_get_secret_string_success(self):
        """Test successful retrieval of string secret"""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': 'test-api-key-value'
        }
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result == 'test-api-key-value'
        mock_client.get_secret_value.assert_called_once_with(SecretId='test-secret')
    
    def test_get_secret_json_with_api_key(self):
        """Test retrieval of JSON secret with standard API key field"""
        secret_json = {
            'api_key': 'json-api-key-value',
            'other_field': 'other_value'
        }
        
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(secret_json)
        }
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result == 'json-api-key-value'
    
    def test_get_secret_json_with_finnhub_key(self):
        """Test retrieval of JSON secret with finnhub_api_key field"""
        secret_json = {
            'finnhub_api_key': 'finnhub-key-value',
            'other_field': 'other_value'
        }
        
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(secret_json)
        }
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result == 'finnhub-key-value'
    
    def test_get_secret_json_no_standard_field(self):
        """Test retrieval of JSON secret without standard API key fields"""
        secret_json = {
            'custom_field': 'custom_value',
            'other_field': 'other_value'
        }
        
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(secret_json)
        }
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        # Should return the entire JSON as string
        assert result == json.dumps(secret_json)
    
    def test_get_secret_binary(self):
        """Test retrieval of binary secret"""
        binary_data = b'binary-api-key'
        
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretBinary': binary_data
        }
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result == 'binary-api-key'
    
    def test_get_secret_not_found(self):
        """Test handling of secret not found error"""
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('nonexistent-secret')
        
        assert result is None
    
    def test_get_secret_decryption_failure(self):
        """Test handling of decryption failure"""
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'DecryptionFailureException'}},
            'GetSecretValue'
        )
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result is None
    
    def test_get_secret_invalid_request(self):
        """Test handling of invalid request error"""
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'InvalidRequestException'}},
            'GetSecretValue'
        )
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result is None
    
    def test_get_secret_unexpected_error(self):
        """Test handling of unexpected errors"""
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = Exception("Unexpected error")
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result is None
    
    def test_get_api_key_success(self):
        """Test successful API key retrieval"""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': 'secret-api-key'
        }
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_api_key('test-secret')
        
        assert result == 'secret-api-key'
    
    def test_get_api_key_with_fallback(self):
        """Test API key retrieval with environment variable fallback"""
        # Mock secrets manager failure
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        
        with patch('boto3.client', return_value=mock_client):
            with patch('os.getenv', return_value='env-api-key'):
                sm = SecretsManager('us-east-1')
                result = sm.get_api_key('test-secret', 'FALLBACK_ENV_VAR')
        
        assert result == 'env-api-key'
    
    def test_get_api_key_no_fallback_success(self):
        """Test API key retrieval without fallback when secrets manager works"""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': 'secret-api-key'
        }
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_api_key('test-secret')
        
        assert result == 'secret-api-key'
    
    def test_get_api_key_both_fail(self):
        """Test API key retrieval when both secrets manager and env var fail"""
        # Mock secrets manager failure
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        
        with patch('boto3.client', return_value=mock_client):
            with patch('os.getenv', return_value=None):
                sm = SecretsManager('us-east-1')
                result = sm.get_api_key('test-secret', 'FALLBACK_ENV_VAR')
        
        assert result is None
    
    def test_get_api_key_no_fallback_specified(self):
        """Test API key retrieval when no fallback is specified and secrets manager fails"""
        # Mock secrets manager failure
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_api_key('test-secret')
        
        assert result is None
    
    def test_get_secret_empty_response(self):
        """Test handling of empty secret response"""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {}
        
        with patch('boto3.client', return_value=mock_client):
            sm = SecretsManager('us-east-1')
            result = sm.get_secret('test-secret')
        
        assert result is None