import json
import os
import logging
from typing import Dict, Any, List
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


def scan_all_urls() -> List[Dict[str, Any]]:
    """
    Perform a DynamoDB Scan operation to retrieve all URL mappings.
    
    Returns:
        List of all items in the table
    """
    try:
        items = []
        response = table.scan()
        items.extend(response.get('Items', []))
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        return items
        
    except ClientError as e:
        logger.error(f"Error scanning table: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for listing all URL mappings.
    
    Args:
        event: Lambda event containing the request
        context: Lambda context
        
    Returns:
        API response with status code and body
    """
    request_id = context.aws_request_id if context else 'local'
    logger.info(f"Processing list URLs request: {request_id}")
    
    try:
        # Retrieve all URL mappings
        items = scan_all_urls()
        logger.info(f"Retrieved {len(items)} URL mappings")
        
        # Build response with formatted URLs
        function_url = event.get('requestContext', {}).get('domainName', 'unknown')
        
        urls = []
        for item in items:
            urls.append({
                'short_code': item['short_code'],
                'short_url': f"https://{function_url}/{item['short_code']}",
                'original_url': item['original_url'],
                'created_at': item['created_at'],
                'access_count': item.get('access_count', 0)
            })
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'urls': urls,
                'count': len(urls)
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
