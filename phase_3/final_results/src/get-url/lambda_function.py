import json
import os
import logging
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


def get_by_short_code(short_code: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve URL mapping by short code using partition key.
    
    Args:
        short_code: The 6-character short code
        
    Returns:
        The item if found, None otherwise
    """
    try:
        response = table.get_item(
            Key={'short_code': short_code}
        )
        
        return response.get('Item')
        
    except ClientError as e:
        logger.error(f"Error retrieving by short code: {e}")
        raise


def get_by_original_url(original_url: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve URL mapping by original URL using GSI.
    
    Args:
        original_url: The original URL
        
    Returns:
        The item if found, None otherwise
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
        logger.error(f"Error retrieving by original URL: {e}")
        raise


def increment_access_count(short_code: str) -> None:
    """
    Increment the access count for a URL mapping using atomic counter.
    
    Args:
        short_code: The short code to update
    """
    try:
        table.update_item(
            Key={'short_code': short_code},
            UpdateExpression='SET access_count = access_count + :inc',
            ExpressionAttributeValues={':inc': 1}
        )
        
    except ClientError as e:
        logger.error(f"Error incrementing access count: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving URL mappings.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API response with status code and body
    """
    request_id = context.aws_request_id if context else 'local'
    logger.info(f"Processing get URL request: {request_id}")
    
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        short_code = query_params.get('short_code', '').strip()
        original_url = query_params.get('url', '').strip()
        
        # Validate that at least one parameter is provided
        if not short_code and not original_url:
            logger.warning("Missing required parameters")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Missing parameters',
                    'message': 'Either short_code or url parameter is required',
                    'request_id': request_id
                }, cls=DecimalEncoder)
            }
        
        # Retrieve the item
        item = None
        if short_code:
            logger.debug(f"Retrieving by short code: {short_code}")
            item = get_by_short_code(short_code)
        else:
            logger.debug(f"Retrieving by original URL: {original_url}")
            item = get_by_original_url(original_url)
        
        # Check if item was found
        if not item:
            logger.info(f"No mapping found for provided identifier")
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Not found',
                    'message': 'No mapping found for the provided identifier',
                    'request_id': request_id
                }, cls=DecimalEncoder)
            }
        
        # Increment access count
        increment_access_count(item['short_code'])
        logger.info(f"Retrieved and incremented access count for: {item['short_code']}")
        
        # Build response
        function_url = event.get('requestContext', {}).get('domainName', 'unknown')
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'short_code': item['short_code'],
                'short_url': f"https://{function_url}/{item['short_code']}",
                'original_url': item['original_url'],
                'created_at': item['created_at'],
                'access_count': item.get('access_count', 0) + 1
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
