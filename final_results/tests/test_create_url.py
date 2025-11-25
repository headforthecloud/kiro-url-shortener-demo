import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
import sys
import os
import importlib.util

# Load the create-url lambda_function module
spec = importlib.util.spec_from_file_location(
    "create_lambda_function",
    os.path.join(os.path.dirname(__file__), '../src/create-url/lambda_function.py')
)
lambda_function = importlib.util.module_from_spec(spec)
sys.modules['create_lambda_function'] = lambda_function
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
def valid_event():
    """Valid Lambda event for creating a URL"""
    return {
        'body': json.dumps({'url': 'https://example.com/long/url'}),
        'requestContext': {
            'domainName': 'test.lambda-url.us-east-1.on.aws'
        }
    }


class TestValidateUrl:
    """Tests for URL validation"""
    
    def test_valid_http_url(self):
        is_valid, error = lambda_function.validate_url('http://example.com')
        assert is_valid is True
        assert error is None
    
    def test_valid_https_url(self):
        is_valid, error = lambda_function.validate_url('https://example.com')
        assert is_valid is True
        assert error is None
    
    def test_invalid_protocol_ftp(self):
        is_valid, error = lambda_function.validate_url('ftp://example.com')
        assert is_valid is False
        assert 'HTTP or HTTPS' in error
    
    def test_invalid_protocol_file(self):
        is_valid, error = lambda_function.validate_url('file:///path/to/file')
        assert is_valid is False
        assert 'HTTP or HTTPS' in error
    
    def test_empty_url(self):
        is_valid, error = lambda_function.validate_url('')
        assert is_valid is False
        assert error is not None
    
    def test_none_url(self):
        is_valid, error = lambda_function.validate_url(None)
        assert is_valid is False
        assert 'required' in error.lower()
    
    def test_whitespace_only_url(self):
        is_valid, error = lambda_function.validate_url('   ')
        assert is_valid is False
        assert 'empty' in error.lower()


class TestGenerateShortCode:
    """Tests for short code generation"""
    
    def test_generates_six_characters(self):
        code = lambda_function.generate_short_code()
        assert len(code) == 6
    
    def test_generates_alphanumeric_only(self):
        code = lambda_function.generate_short_code()
        assert code.isalnum()
    
    def test_generates_different_codes(self):
        codes = [lambda_function.generate_short_code() for _ in range(100)]
        # Should have high uniqueness (not all the same)
        assert len(set(codes)) > 90


class TestCheckUrlExists:
    """Tests for checking URL existence"""
    
    def test_url_exists(self, mock_table):
        mock_table.query.return_value = {
            'Items': [{
                'short_code': 'abc123',
                'original_url': 'https://example.com',
                'created_at': '2025-11-17T10:00:00Z',
                'access_count': 0
            }]
        }
        
        result = lambda_function.check_url_exists('https://example.com')
        
        assert result is not None
        assert result['short_code'] == 'abc123'
        mock_table.query.assert_called_once()
    
    def test_url_does_not_exist(self, mock_table):
        mock_table.query.return_value = {'Items': []}
        
        result = lambda_function.check_url_exists('https://example.com')
        
        assert result is None
    
    def test_dynamodb_error(self, mock_table):
        mock_table.query.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'Query'
        )
        
        with pytest.raises(ClientError):
            lambda_function.check_url_exists('https://example.com')


class TestCreateUrlMapping:
    """Tests for creating URL mappings"""
    
    def test_successful_creation(self, mock_table):
        mock_table.put_item.return_value = {}
        
        result = lambda_function.create_url_mapping('abc123', 'https://example.com')
        
        assert result['short_code'] == 'abc123'
        assert result['original_url'] == 'https://example.com'
        assert result['access_count'] == 0
        assert 'created_at' in result
        mock_table.put_item.assert_called_once()
    
    def test_collision_detection(self, mock_table):
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Item exists'}},
            'PutItem'
        )
        
        with pytest.raises(ValueError, match='collision'):
            lambda_function.create_url_mapping('abc123', 'https://example.com')
    
    def test_dynamodb_error(self, mock_table):
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'PutItem'
        )
        
        with pytest.raises(ClientError):
            lambda_function.create_url_mapping('abc123', 'https://example.com')


class TestLambdaHandler:
    """Tests for the Lambda handler"""
    
    def test_successful_url_creation(self, mock_table, mock_context, valid_event):
        mock_table.query.return_value = {'Items': []}
        mock_table.put_item.return_value = {}
        
        response = lambda_function.lambda_handler(valid_event, mock_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'short_code' in body
        assert body['original_url'] == 'https://example.com/long/url'
        assert 'short_url' in body
        assert 'created_at' in body
    
    def test_duplicate_url_returns_existing(self, mock_table, mock_context, valid_event):
        mock_table.query.return_value = {
            'Items': [{
                'short_code': 'abc123',
                'original_url': 'https://example.com/long/url',
                'created_at': '2025-11-17T10:00:00Z',
                'access_count': 5
            }]
        }
        
        response = lambda_function.lambda_handler(valid_event, mock_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['short_code'] == 'abc123'
        assert body['original_url'] == 'https://example.com/long/url'
    
    def test_invalid_url_format(self, mock_table, mock_context):
        event = {
            'body': json.dumps({'url': 'ftp://example.com'}),
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'Invalid URL format' in body['error']
    
    def test_missing_url(self, mock_table, mock_context):
        event = {
            'body': json.dumps({}),
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_invalid_json_body(self, mock_table, mock_context):
        event = {
            'body': 'not valid json',
            'requestContext': {'domainName': 'test.lambda-url.us-east-1.on.aws'}
        }
        
        response = lambda_function.lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_collision_retry_success(self, mock_table, mock_context, valid_event):
        mock_table.query.return_value = {'Items': []}
        
        # First attempt fails with collision, second succeeds
        mock_table.put_item.side_effect = [
            ClientError(
                {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Item exists'}},
                'PutItem'
            ),
            {}
        ]
        
        response = lambda_function.lambda_handler(valid_event, mock_context)
        
        assert response['statusCode'] == 201
        assert mock_table.put_item.call_count == 2
    
    def test_collision_retry_exhausted(self, mock_table, mock_context, valid_event):
        mock_table.query.return_value = {'Items': []}
        
        # All attempts fail with collision
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Item exists'}},
            'PutItem'
        )
        
        response = lambda_function.lambda_handler(valid_event, mock_context)
        
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'Collision failure' in body['error']
        assert mock_table.put_item.call_count == 5
    
    def test_dynamodb_service_unavailable(self, mock_table, mock_context, valid_event):
        mock_table.query.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'Query'
        )
        
        response = lambda_function.lambda_handler(valid_event, mock_context)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'Service unavailable' in body['error']
