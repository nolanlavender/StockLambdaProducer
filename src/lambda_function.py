import json
import boto3
import logging
import os
from datetime import datetime
from typing import Dict, List, Any
import requests
from config import Config
from market_hours import MarketHours

logger = logging.getLogger()
logger.setLevel(logging.INFO)

kinesis_client = boto3.client('kinesis')

def lambda_handler(event, context):
    """
    AWS Lambda handler function that fetches stock prices and sends them to Kinesis
    Only runs during market hours unless test mode is enabled
    """
    try:
        config = Config()
        market_hours = MarketHours()
        
        # Load API key from Secrets Manager or environment variable
        config.load_api_key()
        
        logger.info(f"Lambda execution started - Config: {config.to_dict()}")
        
        # Check market hours unless in test mode
        if config.enforce_market_hours and not config.test_mode:
            is_market_open, reason = market_hours.is_market_open()
            market_hours.log_market_status()
            
            if not is_market_open:
                logger.info(f"Skipping execution: {reason}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': f'Execution skipped: {reason}',
                        'market_status': 'closed',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }
        elif config.test_mode:
            logger.info("Running in TEST MODE - market hours check bypassed")
        else:
            logger.info("Market hours enforcement disabled")
        
        logger.info(f"Fetching stock prices for {len(config.stock_symbols)} symbols")
        
        stock_data = fetch_stock_prices(config.stock_symbols, config.api_key)
        
        if stock_data:
            send_to_kinesis(stock_data, config.kinesis_stream_name)
            logger.info(f"Successfully sent {len(stock_data)} stock records to Kinesis")
        else:
            logger.warning("No stock data retrieved")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {len(stock_data)} stock prices',
                'records_processed': len(stock_data),
                'test_mode': config.test_mode,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

def fetch_stock_prices(symbols: List[str], api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch stock prices from Finnhub API
    """
    stock_data = []
    
    for symbol in symbols:
        try:
            url = f"https://finnhub.io/api/v1/quote"
            params = {
                'symbol': symbol,
                'token': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if we got valid data (Finnhub returns 'c' for current price)
            if 'c' in data and data['c'] is not None and data['c'] > 0:
                current_price = data['c']
                previous_close = data.get('pc', current_price)
                change = current_price - previous_close
                change_percent = (change / previous_close * 100) if previous_close > 0 else 0
                
                stock_record = {
                    'symbol': symbol,
                    'price': current_price,
                    'change': change,
                    'change_percent': f"{change_percent:.2f}",
                    'high': data.get('h', current_price),
                    'low': data.get('l', current_price),
                    'open': data.get('o', current_price),
                    'previous_close': previous_close,
                    'timestamp': datetime.utcnow().isoformat()
                }
                stock_data.append(stock_record)
                logger.info(f"Fetched data for {symbol}: ${stock_record['price']}")
            else:
                logger.warning(f"No valid data returned for symbol {symbol}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for symbol {symbol}: {str(e)}")
        except (ValueError, KeyError) as e:
            logger.error(f"Data parsing error for symbol {symbol}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error for symbol {symbol}: {str(e)}")
    
    return stock_data

def send_to_kinesis(stock_data: List[Dict[str, Any]], stream_name: str) -> None:
    """
    Send stock data records to Kinesis Data Stream
    """
    records = []
    
    for stock in stock_data:
        record = {
            'Data': json.dumps(stock),
            'PartitionKey': stock['symbol']
        }
        records.append(record)
    
    try:
        response = kinesis_client.put_records(
            Records=records,
            StreamName=stream_name
        )
        
        failed_count = response.get('FailedRecordCount', 0)
        if failed_count > 0:
            logger.warning(f"Failed to send {failed_count} records to Kinesis")
        else:
            logger.info(f"Successfully sent all {len(records)} records to Kinesis stream {stream_name}")
            
    except Exception as e:
        logger.error(f"Error sending records to Kinesis: {str(e)}")
        raise