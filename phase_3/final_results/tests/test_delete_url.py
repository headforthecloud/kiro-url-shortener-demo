import json
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
import sys
import os
import importlib.util

# Load the delete-url lambda_function module
spec = importlib.util.spec_from_file_location(
    "delete_lambda_function",
    os.path.join(os.path.dirname(__file__), '../src/delete-url/lambda_function.py')
)
lambda_function = importlib.util.module_from_spec(spec)
sys.modules['delete_lambda_function'] = lambda_function
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
def sample_item():
    """Sample DynamoDB item"""
    return {
        'short_code': 'abc123',
        'original_url': 'https://example.com/long/url',
        'created_at': '2025-11-17T10:00:00Z',
        'access_count': 5
    }


class TestFindShortCodeByUrl:
    """Tests for finding short code by URL"""
    
    def test_successful_lookup(self, mock_table, sample_item):
        mock_table.query.return_value = {'Items': [sample_item]}
        
        result = lambda_function.find_short_code_by_url('https://example.com/long/url')
        
        assert result == 'abc123'
        mock_table.query.assert_called_once()
    
    def test_url_not_found(self, mock_table):
        mock_table.query.return_value = {'Items': []}
        
        result = lambda_function.find_short_code_by_url('https://example.com/not/found')
        
        assert result is None
    
    def test_dynamodb_error(self, mock_table):
        mock_table.query.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'Query'
        )
        
        with pytest.raises(ClientError):
            lambda_function.find_short_code_by_url('https://example.com/long/url')


class TestDeleteUrlMapping:
    """Tests for deleting URL mappings"""
    
    def test_successful_deletion(self, mock_table):
        mock_table.delete_item.return_value = {}
        
        lambda_function.delete_url_mapping('abc123')
        
        mock_table.delete_item.assert_called_once_with(
            Key={'short_code': 'abc123'}
        )
    
    def test_dynamodb_error(self, mock_table):
        mock_table.delete_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'DeleteItem'
        )
        
        with pytest.raises(ClientError):
            lambda_function.delete_url_mapping('abc123')


class TestLambdaHandler:
    """Tests for the Lambda handler"""
    
    def test_successful_deletion(self, mock_table, mock_context, sample_item):
        event = {
            'queryStringParameters': {'url': 'https://example.com/long/url'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.query.return_value = {'Items': [sample_item]}
        mock_table.delete_item.return_value = {}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'URL mapping deleted successfully'
        assert body['short_code'] == 'abc123'
        assert body['original_url'] == 'https://example.com/long/url'
        
        # Verify both query and delete were called
        mock_table.query.assert_called_once()
        mock_table.delete_item.assert_called_once()
    
    def test_missing_url_parameter(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Missing parameter' in body['error']
    
    def test_none_query_parameters(self, mock_table, mock_context):
        event = {
            'queryStringParameters': None,
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Missing parameter' in body['error']
    
    def test_url_not_found(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {'url': 'https://example.com/not/found'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.query.return_value = {'Items': []}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Not found' in body['error']
    
    def test_dynamodb_error_on_query(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {'url': 'https://example.com/long/url'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.query.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'Query'
        )
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'Service unavailable' in body['error']
    
    def test_dynamodb_error_on_delete(self, mock_table, mock_context, sample_item):
        event = {
            'queryStringParameters': {'url': 'https://example.com/long/url'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.query.return_value = {'Items': [sample_item]}
        mock_table.delete_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'DeleteItem'
        )
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'Service unavailable' in body['error']
    
    def test_whitespace_url_parameter(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {'url': '   '},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Missing parameter' in body['error']
