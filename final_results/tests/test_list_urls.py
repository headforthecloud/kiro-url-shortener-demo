import json
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
import sys
import os
import importlib.util

# Load the list-urls lambda_function module
spec = importlib.util.spec_from_file_location(
    "list_lambda_function",
    os.path.join(os.path.dirname(__file__), '../src/list-urls/lambda_function.py')
)
lambda_function = importlib.util.module_from_spec(spec)
sys.modules['list_lambda_function'] = lambda_function
spec.loader.exec_module(lambda_function)


@pytest.fixture
def mock_table():
    """Mock DynamoDB table"""
    with patch.object(lambda_function, 'table') as mock:
        yield mock


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    context = Mock()
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture
def sample_items():
    """Sample DynamoDB items"""
    return [
        {
            'short_code': 'abc123',
            'original_url': 'https://example.com/first',
            'created_at': '2025-11-17T10:00:00Z',
            'access_count': 5
        },
        {
            'short_code': 'xyz789',
            'original_url': 'https://example.com/second',
            'created_at': '2025-11-17T11:00:00Z',
            'access_count': 10
        },
        {
            'short_code': 'def456',
            'original_url': 'https://example.com/third',
            'created_at': '2025-11-17T12:00:00Z',
            'access_count': 0
        }
    ]


class TestScanAllUrls:
    """Tests for scanning all URLs"""
    
    def test_successful_scan_single_page(self, mock_table, sample_items):
        mock_table.scan.return_value = {'Items': sample_items}
        
        result = lambda_function.scan_all_urls()
        
        assert len(result) == 3
        assert result[0]['short_code'] == 'abc123'
        assert result[1]['short_code'] == 'xyz789'
        assert result[2]['short_code'] == 'def456'
        mock_table.scan.assert_called_once()
    
    def test_successful_scan_with_pagination(self, mock_table, sample_items):
        # First page
        mock_table.scan.side_effect = [
            {
                'Items': sample_items[:2],
                'LastEvaluatedKey': {'short_code': 'xyz789'}
            },
            # Second page
            {
                'Items': sample_items[2:]
            }
        ]
        
        result = lambda_function.scan_all_urls()
        
        assert len(result) == 3
        assert mock_table.scan.call_count == 2
        # Verify second call included ExclusiveStartKey
        second_call_kwargs = mock_table.scan.call_args_list[1][1]
        assert 'ExclusiveStartKey' in second_call_kwargs
        assert second_call_kwargs['ExclusiveStartKey'] == {'short_code': 'xyz789'}
    
    def test_empty_table(self, mock_table):
        mock_table.scan.return_value = {'Items': []}
        
        result = lambda_function.scan_all_urls()
        
        assert len(result) == 0
        assert result == []
        mock_table.scan.assert_called_once()
    
    def test_dynamodb_error(self, mock_table):
        mock_table.scan.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'Scan'
        )
        
        with pytest.raises(ClientError):
            lambda_function.scan_all_urls()


class TestLambdaHandler:
    """Tests for the Lambda handler"""
    
    def test_list_multiple_items(self, mock_table, mock_context, sample_items):
        event = {
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.scan.return_value = {'Items': sample_items}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'urls' in body
        assert 'count' in body
        assert body['count'] == 3
        assert len(body['urls']) == 3
        
        # Verify first item structure
        first_url = body['urls'][0]
        assert first_url['short_code'] == 'abc123'
        assert first_url['original_url'] == 'https://example.com/first'
        assert first_url['created_at'] == '2025-11-17T10:00:00Z'
        assert first_url['access_count'] == 5
        assert 'short_url' in first_url
        assert 'test.lambda-url.us-east-1.on.aws' in first_url['short_url']
    
    def test_list_empty_table(self, mock_table, mock_context):
        event = {
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.scan.return_value = {'Items': []}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['urls'] == []
        assert body['count'] == 0
    
    def test_list_single_item(self, mock_table, mock_context, sample_items):
        event = {
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.scan.return_value = {'Items': [sample_items[0]]}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 1
        assert len(body['urls']) == 1
        assert body['urls'][0]['short_code'] == 'abc123'
    
    def test_dynamodb_error(self, mock_table, mock_context):
        event = {
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.scan.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'Scan'
        )
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'Service unavailable' in body['error']
        assert 'request_id' in body
    
    def test_missing_request_context(self, mock_table, mock_context, sample_items):
        event = {}
        
        mock_table.scan.return_value = {'Items': sample_items}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 3
        # Should handle missing domainName gracefully
        assert 'unknown' in body['urls'][0]['short_url']
    
    def test_items_without_access_count(self, mock_table, mock_context):
        event = {
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        # Item without access_count field
        items = [
            {
                'short_code': 'abc123',
                'original_url': 'https://example.com/first',
                'created_at': '2025-11-17T10:00:00Z'
            }
        ]
        
        mock_table.scan.return_value = {'Items': items}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['urls'][0]['access_count'] == 0  # Should default to 0
