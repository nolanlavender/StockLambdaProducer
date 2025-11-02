import boto3
import json
import logging
from typing import Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SecretsManager:
    """
    Utility class for retrieving secrets from AWS Secrets Manager
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        self.secrets_client = boto3.client('secretsmanager', region_name=region_name)
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a secret value from AWS Secrets Manager
        
        Args:
            secret_name: The name or ARN of the secret
            
        Returns:
            The secret value as a string, or None if retrieval fails
        """
        try:
            logger.info(f"Retrieving secret: {secret_name}")
            
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            
            # Handle both string and JSON secrets
            secret_value = response.get('SecretString')
            
            if secret_value:
                try:
                    # Try to parse as JSON first
                    secret_json = json.loads(secret_value)
                    # If it's a JSON object, look for common API key field names
                    if isinstance(secret_json, dict):
                        for key in ['api_key', 'apikey', 'key', 'token', 'finnhub_api_key']:
                            if key in secret_json:
                                logger.info(f"Found API key in JSON secret under key: {key}")
                                return secret_json[key]
                        # If no standard key found, return the whole JSON as string
                        logger.warning("No standard API key field found in JSON secret")
                        return secret_value
                    else:
                        return secret_value
                except json.JSONDecodeError:
                    # It's a plain string secret
                    logger.info("Retrieved plain string secret")
                    return secret_value
            
            # Handle binary secrets (though rare for API keys)
            binary_secret = response.get('SecretBinary')
            if binary_secret:
                logger.info("Retrieved binary secret, decoding as UTF-8")
                return binary_secret.decode('utf-8')
            
            logger.error(f"No secret value found in response for {secret_name}")
            return None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error(f"Secret not found: {secret_name}")
            elif error_code == 'InvalidRequestException':
                logger.error(f"Invalid request for secret: {secret_name}")
            elif error_code == 'InvalidParameterException':
                logger.error(f"Invalid parameter for secret: {secret_name}")
            elif error_code == 'DecryptionFailureException':
                logger.error(f"Decryption failed for secret: {secret_name}")
            elif error_code == 'InternalServiceErrorException':
                logger.error(f"Internal service error retrieving secret: {secret_name}")
            else:
                logger.error(f"Unexpected error retrieving secret {secret_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret {secret_name}: {e}")
            return None
    
    def get_api_key(self, secret_name: str, fallback_env_var: Optional[str] = None) -> Optional[str]:
        """
        Get API key from Secrets Manager with optional environment variable fallback
        
        Args:
            secret_name: The name of the secret containing the API key
            fallback_env_var: Optional environment variable to check if secret retrieval fails
            
        Returns:
            The API key value or None if not found
        """
        import os
        
        # First try Secrets Manager
        api_key = self.get_secret(secret_name)
        
        if api_key:
            logger.info("Successfully retrieved API key from Secrets Manager")
            return api_key
        
        # Fallback to environment variable if specified
        if fallback_env_var:
            logger.warning(f"Failed to retrieve from Secrets Manager, checking environment variable: {fallback_env_var}")
            env_key = os.getenv(fallback_env_var)
            if env_key:
                logger.info("Successfully retrieved API key from environment variable")
                return env_key
            else:
                logger.error(f"Environment variable {fallback_env_var} not set")
        
        logger.error("Failed to retrieve API key from both Secrets Manager and environment variable")
        return None