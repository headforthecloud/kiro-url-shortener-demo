import json
import os
import logging
import random
import string
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger.setLevel(getattr(logging, log_level))

# Initialize DynamoDB client outside handler for connection reuse
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name) if table_name else None


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types from DynamoDB"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert to int if it's a whole number, otherwise float
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate that the URL uses HTTP or HTTPS protocol.
    
    Args:
        url: The URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL is required and must be a string"
    
    url = url.strip()
    if not url:
        return False, "URL cannot be empty"
    
    if not (url.startswith('http://') or url.startswith('https://')):
        return False, "URL must use HTTP or HTTPS protocol"
    
    return True, None


def generate_short_code() -> str:
    """
    Generate a random 6-character alphanumeric short code.
    
    Returns:
        A 6-character string containing letters (a-z, A-Z) and digits (0-9)
    """
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(6))


def check_url_exists(original_url: str) -> Optional[Dict[str, Any]]:
    """
    Check if a URL already exists in the database using the GSI.
    
    Args:
        original_url: The original URL to check
        
    Returns:
        The existing item if found, None otherwise
    """
    try:
        response = table.query(
            IndexName='OriginalURLIndex',
            KeyConditionExpression='original_url = :url',
            ExpressionAttributeValues={
                ':url': original_url
            }
        )
        
        items = response.get('Items', [])
        return items[0] if items else None
        
    except ClientError as e:
        logger.error(f"Error checking URL existence: {e}")
        raise


def create_url_mapping(short_code: str, original_url: str) -> Dict[str, Any]:
    """
    Create a new URL mapping in DynamoDB.
    
    Args:
        short_code: The generated short code
        original_url: The original URL
        
    Returns:
        The created item
    """
    created_at = datetime.now(timezone.utc).isoformat()
    
    item = {
        'short_code': short_code,
        'original_url': original_url,
        'created_at': created_at,
        'access_count': 0
    }
    
    try:
        table.put_item(
            Item=item,
            ConditionExpression='attribute_not_exists(short_code)'
        )
        return item
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # Short code collision
            raise ValueError("Short code collision detected")
        logger.error(f"Error creating URL mapping: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for creating shortened URLs.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API response with status code and body
    """
    request_id = context.aws_request_id if context else 'local'
    logger.info(f"Processing create URL request: {request_id}")
    
    try:
        # Parse request body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        original_url = body.get('url', '').strip()
        
        # Validate URL
        is_valid, error_message = validate_url(original_url)
        if not is_valid:
            logger.warning(f"Invalid URL format: {error_message}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Invalid URL format',
                    'message': error_message,
                    'request_id': request_id
                }, cls=DecimalEncoder)
            }
        
        # Check if URL already exists
        existing_item = check_url_exists(original_url)
        if existing_item:
            logger.info(f"URL already exists with short code: {existing_item['short_code']}")
            function_url = event.get('requestContext', {}).get('domainName', 'unknown')
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'short_code': existing_item['short_code'],
                    'short_url': f"https://{function_url}/{existing_item['short_code']}",
                    'original_url': existing_item['original_url'],
                    'created_at': existing_item['created_at']
                }, cls=DecimalEncoder)
            }
        
        # Generate short code with collision detection
        max_retries = 5
        item = None
        
        for attempt in range(max_retries):
            try:
                short_code = generate_short_code()
                logger.debug(f"Generated short code: {short_code} (attempt {attempt + 1})")
                
                item = create_url_mapping(short_code, original_url)
                logger.info(f"Created URL mapping: {short_code} -> {original_url}")
                break
                
            except ValueError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Short code collision on attempt {attempt + 1}, retrying...")
                    continue
                else:
                    logger.error(f"Failed to generate unique short code after {max_retries} attempts")
                    return {
                        'statusCode': 409,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': 'Collision failure',
                            'message': f'Failed to generate unique short code after {max_retries} attempts',
                            'request_id': request_id
                        }, cls=DecimalEncoder)
                    }
        
        # Build response
        function_url = event.get('requestContext', {}).get('domainName', 'unknown')
        
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'short_code': item['short_code'],
                'short_url': f"https://{function_url}/{item['short_code']}",
                'original_url': item['original_url'],
                'created_at': item['created_at']
            }, cls=DecimalEncoder)
        }
        
    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        return {
            'statusCode': 503,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Service unavailable',
                'message': 'Database service is temporarily unavailable',
                'request_id': request_id
            }, cls=DecimalEncoder)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Invalid request',
                'message': 'Request body must be valid JSON',
                'request_id': request_id
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred',
                'request_id': request_id
            }, cls=DecimalEncoder)
        }
