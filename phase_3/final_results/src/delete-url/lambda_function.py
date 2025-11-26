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


def find_short_code_by_url(original_url: str) -> Optional[str]:
    """
    Find the short code for a given original URL using GSI.
    
    Args:
        original_url: The original URL to look up
        
    Returns:
        The short code if found, None otherwise
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
        return items[0]['short_code'] if items else None
        
    except ClientError as e:
        logger.error(f"Error finding short code by URL: {e}")
        raise


def delete_url_mapping(short_code: str) -> None:
    """
    Delete a URL mapping from DynamoDB.
    
    Args:
        short_code: The short code to delete
    """
    try:
        table.delete_item(
            Key={'short_code': short_code}
        )
        
    except ClientError as e:
        logger.error(f"Error deleting URL mapping: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for deleting URL mappings.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API response with status code and body
    """
    request_id = context.aws_request_id if context else 'local'
    logger.info(f"Processing delete URL request: {request_id}")
    
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        original_url = query_params.get('url', '').strip()
        
        # Validate that URL parameter is provided
        if not original_url:
            logger.warning("Missing required parameter: url")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Missing parameter',
                    'message': 'The url parameter is required',
                    'request_id': request_id
                }, cls=DecimalEncoder)
            }
        
        # Find the short code for the URL
        logger.debug(f"Finding short code for URL: {original_url}")
        short_code = find_short_code_by_url(original_url)
        
        # Check if URL exists
        if not short_code:
            logger.info(f"No mapping found for URL: {original_url}")
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Not found',
                    'message': 'No mapping found for the provided URL',
                    'request_id': request_id
                }, cls=DecimalEncoder)
            }
        
        # Delete the mapping
        delete_url_mapping(short_code)
        logger.info(f"Deleted URL mapping: {short_code} -> {original_url}")
        
        # Build response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'URL mapping deleted successfully',
                'short_code': short_code,
                'original_url': original_url
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
