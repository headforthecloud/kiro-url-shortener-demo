import json
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
import sys
import os
import importlib.util

# Load the get-url lambda_function module
spec = importlib.util.spec_from_file_location(
    "get_lambda_function",
    os.path.join(os.path.dirname(__file__), '../src/get-url/lambda_function.py')
)
lambda_function = importlib.util.module_from_spec(spec)
sys.modules['get_lambda_function'] = lambda_function
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


class TestGetByShortCode:
    """Tests for retrieving by short code"""
    
    def test_successful_retrieval(self, mock_table, sample_item):
        mock_table.get_item.return_value = {'Item': sample_item}
        
        result = lambda_function.get_by_short_code('abc123')
        
        assert result is not None
        assert result['short_code'] == 'abc123'
        mock_table.get_item.assert_called_once_with(
            Key={'short_code': 'abc123'}
        )
    
    def test_not_found(self, mock_table):
        mock_table.get_item.return_value = {}
        
        result = lambda_function.get_by_short_code('xyz789')
        
        assert result is None
    
    def test_dynamodb_error(self, mock_table):
        mock_table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'GetItem'
        )
        
        with pytest.raises(ClientError):
            lambda_function.get_by_short_code('abc123')


class TestGetByOriginalUrl:
    """Tests for retrieving by original URL"""
    
    def test_successful_retrieval(self, mock_table, sample_item):
        mock_table.query.return_value = {'Items': [sample_item]}
        
        result = lambda_function.get_by_original_url('https://example.com/long/url')
        
        assert result is not None
        assert result['short_code'] == 'abc123'
        mock_table.query.assert_called_once()
    
    def test_not_found(self, mock_table):
        mock_table.query.return_value = {'Items': []}
        
        result = lambda_function.get_by_original_url('https://example.com/not/found')
        
        assert result is None
    
    def test_dynamodb_error(self, mock_table):
        mock_table.query.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'Query'
        )
        
        with pytest.raises(ClientError):
            lambda_function.get_by_original_url('https://example.com/long/url')


class TestIncrementAccessCount:
    """Tests for incrementing access count"""
    
    def test_successful_increment(self, mock_table):
        mock_table.update_item.return_value = {}
        
        lambda_function.increment_access_count('abc123')
        
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert call_args[1]['Key'] == {'short_code': 'abc123'}
        assert ':inc' in call_args[1]['ExpressionAttributeValues']
        assert call_args[1]['ExpressionAttributeValues'][':inc'] == 1
    
    def test_dynamodb_error(self, mock_table):
        mock_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'UpdateItem'
        )
        
        with pytest.raises(ClientError):
            lambda_function.increment_access_count('abc123')


class TestLambdaHandler:
    """Tests for the Lambda handler"""
    
    def test_get_by_short_code_success(self, mock_table, mock_context, sample_item):
        event = {
            'queryStringParameters': {'short_code': 'abc123'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.get_item.return_value = {'Item': sample_item}
        mock_table.update_item.return_value = {}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['short_code'] == 'abc123'
        assert body['original_url'] == 'https://example.com/long/url'
        assert body['access_count'] == 6  # Original 5 + 1
        assert 'short_url' in body
        assert 'created_at' in body
        
        # Verify access count was incremented
        mock_table.update_item.assert_called_once()
    
    def test_get_by_original_url_success(self, mock_table, mock_context, sample_item):
        event = {
            'queryStringParameters': {'url': 'https://example.com/long/url'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.query.return_value = {'Items': [sample_item]}
        mock_table.update_item.return_value = {}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['short_code'] == 'abc123'
        assert body['original_url'] == 'https://example.com/long/url'
        assert body['access_count'] == 6
        
        # Verify access count was incremented
        mock_table.update_item.assert_called_once()
    
    def test_missing_parameters(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Missing parameters' in body['error']
    
    def test_none_query_parameters(self, mock_table, mock_context):
        event = {
            'queryStringParameters': None,
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Missing parameters' in body['error']
    
    def test_short_code_not_found(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {'short_code': 'xyz789'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.get_item.return_value = {}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Not found' in body['error']
    
    def test_original_url_not_found(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {'url': 'https://example.com/not/found'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.query.return_value = {'Items': []}
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Not found' in body['error']
    
    def test_dynamodb_error_on_get(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {'short_code': 'abc123'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'GetItem'
        )
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'Service unavailable' in body['error']
    
    def test_dynamodb_error_on_increment(self, mock_table, mock_context, sample_item):
        event = {
            'queryStringParameters': {'short_code': 'abc123'},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        mock_table.get_item.return_value = {'Item': sample_item}
        mock_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'UpdateItem'
        )
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'Service unavailable' in body['error']
    
    def test_whitespace_parameters(self, mock_table, mock_context):
        event = {
            'queryStringParameters': {'short_code': '   ', 'url': '   '},
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Missing parameters' in body['error']
