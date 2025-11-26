# URL Shortener API

A serverless URL shortening service built with AWS Lambda, DynamoDB, and SAM (Serverless Application Model). This proof-of-concept provides RESTful API endpoints to create shortened URLs, retrieve original URLs, list all mappings, and delete URLs.

## Architecture Overview

```
┌─────────────┐
│ API Client  │
└──────┬──────┘
       │
       ├──────POST────────► Create Lambda (Function URL)
       │                          │
       ├──────GET─────────► Get Lambda (Function URL)
       │                          │
       ├──────GET─────────► List Lambda (Function URL)
       │                          │
       └──────DELETE──────► Delete Lambda (Function URL)
                                  │
                                  ▼
                          ┌───────────────┐
                          │   DynamoDB    │
                          │ URLMappings   │
                          │  Table        │
                          └───────────────┘
```

### Key Components

- **Lambda Functions**: Four separate functions handling Create, Get, List, and Delete operations
- **Function URLs**: Direct HTTPS endpoints for each Lambda (no API Gateway required)
- **DynamoDB**: Single table with Global Secondary Index for bidirectional lookups
- **CloudWatch Logs**: Structured logging for all operations
- **SAM**: Infrastructure as Code for consistent deployments

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13**: Required runtime for Lambda functions
- **pyenv**: Python version manager for managing Python 3.13
  ```bash
  # Install pyenv (macOS)
  brew install pyenv
  
  # Install Python 3.13
  pyenv install 3.13
  ```

- **AWS CLI**: Command-line tool for AWS operations
  ```bash
  # Install AWS CLI (macOS)
  brew install awscli
  
  # Configure AWS credentials
  aws configure
  ```

- **SAM CLI**: AWS Serverless Application Model CLI
  ```bash
  # Install SAM CLI (macOS)
  brew install aws-sam-cli
  
  # Verify installation
  sam --version
  ```

- **AWS Account**: Active AWS account with appropriate permissions
  - DynamoDB table creation
  - Lambda function deployment
  - IAM role creation
  - CloudWatch Logs access

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd url-shortener-api
```

### 2. Set Python Version

```bash
# Set local Python version to 3.13
pyenv local 3.13
```

### 3. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
```

### 4. Install Test Dependencies

```bash
# Install pytest and coverage tools
pip install -r tests/requirements.txt
```

### 5. Run Tests

```bash
# Run all tests with coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_create_url.py -v

# Run tests with detailed output
pytest tests/ -v --cov=src --cov-report=html
```

Expected output:
```
tests/test_create_url.py ........                                        [ 25%]
tests/test_delete_url.py ......                                          [ 50%]
tests/test_get_url.py ........                                           [ 75%]
tests/test_list_urls.py ....                                             [100%]

---------- coverage: platform darwin, python 3.13.0 -----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src/create-url/lambda_function.py         120      8    93%
src/delete-url/lambda_function.py          85      6    93%
src/get-url/lambda_function.py            110      7    94%
src/list-urls/lambda_function.py           65      4    94%
-----------------------------------------------------------
TOTAL                                     380     25    93%
```

## Deployment

### 1. Build the Application

```bash
# Navigate to cloudformation directory
cd cloudformation

# Build SAM application
sam build
```

### 2. Deploy with Guided Setup

```bash
# Deploy with interactive prompts (first time)
sam deploy --guided
```

You'll be prompted for:
- **Stack Name**: e.g., `url-shortener-stack`
- **AWS Region**: e.g., `us-east-1`
- **ProjectName**: e.g., `url-shortener` (default)
- **LogRetentionDays**: e.g., `7` (default)
- **AWSAccountId**: Your 12-digit AWS account ID
- **Confirm changes**: Review and confirm
- **Allow SAM CLI IAM role creation**: Yes
- **Save arguments to configuration**: Yes

### 3. Subsequent Deployments

```bash
# Use saved configuration
sam deploy
```

### 4. Retrieve API Endpoints

After deployment, SAM outputs the Function URLs:

```bash
# View stack outputs
aws cloudformation describe-stacks \
  --stack-name url-shortener-stack \
  --query 'Stacks[0].Outputs' \
  --output table
```

Save these endpoints for API testing:
- `CreateURLEndpoint`
- `GetURLEndpoint`
- `ListURLsEndpoint`
- `DeleteURLEndpoint`

## API Endpoints

### 1. Create Shortened URL

Creates a new shortened URL or returns existing mapping for duplicate URLs.

**Endpoint**: `POST {CreateURLEndpoint}`

**Request Body**:
```json
{
  "url": "https://example.com/very/long/url/path"
}
```

**Success Response** (201 Created):
```json
{
  "short_code": "abc123",
  "short_url": "https://<function-url>/abc123",
  "original_url": "https://example.com/very/long/url/path",
  "created_at": "2025-11-19T10:30:00Z"
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "Invalid URL format",
  "message": "URL must use HTTP or HTTPS protocol"
}
```

**curl Example**:
```bash
curl -X POST https://your-create-function-url.lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/url"}'
```

### 2. Get URL Mapping

Retrieves URL mapping by short code or original URL.

**Endpoint**: `GET {GetURLEndpoint}?short_code=abc123` or `GET {GetURLEndpoint}?url=https://example.com/...`

**Query Parameters**:
- `short_code`: The 6-character short code (e.g., `abc123`)
- `url`: The original URL (URL-encoded)

**Success Response** (200 OK):
```json
{
  "short_code": "abc123",
  "short_url": "https://<function-url>/abc123",
  "original_url": "https://example.com/very/long/url/path",
  "created_at": "2025-11-19T10:30:00Z",
  "access_count": 5
}
```

**Error Response** (404 Not Found):
```json
{
  "error": "Not found",
  "message": "No mapping found for the provided identifier"
}
```

**curl Examples**:
```bash
# Get by short code
curl "https://your-get-function-url.lambda-url.us-east-1.on.aws/?short_code=abc123"

# Get by original URL (URL-encoded)
curl "https://your-get-function-url.lambda-url.us-east-1.on.aws/?url=https%3A%2F%2Fexample.com%2Fvery%2Flong%2Furl"
```

### 3. List All URLs

Retrieves all URL mappings in the system.

**Endpoint**: `GET {ListURLsEndpoint}`

**Success Response** (200 OK):
```json
{
  "urls": [
    {
      "short_code": "abc123",
      "short_url": "https://<function-url>/abc123",
      "original_url": "https://example.com/very/long/url",
      "created_at": "2025-11-19T10:30:00Z",
      "access_count": 5
    },
    {
      "short_code": "xyz789",
      "short_url": "https://<function-url>/xyz789",
      "original_url": "https://another-example.com/path",
      "created_at": "2025-11-19T11:00:00Z",
      "access_count": 2
    }
  ],
  "count": 2
}
```

**curl Example**:
```bash
curl "https://your-list-function-url.lambda-url.us-east-1.on.aws/"
```

### 4. Delete URL Mapping

Deletes a URL mapping by original URL.

**Endpoint**: `DELETE {DeleteURLEndpoint}?url=https://example.com/...`

**Query Parameters**:
- `url`: The original URL to delete (URL-encoded)

**Success Response** (200 OK):
```json
{
  "message": "URL mapping deleted successfully",
  "short_code": "abc123",
  "original_url": "https://example.com/very/long/url"
}
```

**Error Response** (404 Not Found):
```json
{
  "error": "Not found",
  "message": "No mapping found for the provided URL"
}
```

**curl Example**:
```bash
curl -X DELETE "https://your-delete-function-url.lambda-url.us-east-1.on.aws/?url=https%3A%2F%2Fexample.com%2Fvery%2Flong%2Furl"
```

## DynamoDB Schema

### Table: URLMappings

**Table Name**: `{project_name}-{aws_region}-{aws_account_id}-url-mappings`

**Partition Key**: `short_code` (String)

**Global Secondary Index**: `OriginalURLIndex`
- **Partition Key**: `original_url` (String)
- **Projection**: ALL

### Item Attributes

| Attribute      | Type   | Required | Description                                    |
|----------------|--------|----------|------------------------------------------------|
| short_code     | String | Yes      | Unique 6-character alphanumeric identifier     |
| original_url   | String | Yes      | Full URL to be shortened                       |
| created_at     | String | Yes      | ISO 8601 timestamp of creation                 |
| access_count   | Number | Yes      | Number of times the mapping has been retrieved |

### Example Item

```json
{
  "short_code": "abc123",
  "original_url": "https://example.com/very/long/url/path",
  "created_at": "2025-11-19T10:30:00.123Z",
  "access_count": 5
}
```

### Access Patterns

1. **Get by short code**: Direct query using partition key (`short_code`)
2. **Get by original URL**: Query using GSI (`OriginalURLIndex`)
3. **Check if URL exists**: Query using GSI before creating new mapping
4. **List all URLs**: Scan operation (use sparingly in production)
5. **Delete by original URL**: Query GSI to find `short_code`, then delete by partition key

### Billing Mode

**PAY_PER_REQUEST**: Automatic scaling with no capacity planning required. You pay only for the read and write requests you consume.

## Project Structure

```
.
├── .kiro/                              # Kiro configuration and specs
│   ├── specs/url-shortener-api/        # Feature specifications
│   └── steering/                       # AI assistant rules
├── .venv/                              # Python virtual environment (Python 3.13)
├── src/                                # Lambda source code
│   ├── create-url/                     # Create URL Lambda
│   │   ├── lambda_function.py          # Handler implementation
│   │   └── requirements.txt            # boto3 dependency
│   ├── get-url/                        # Get URL Lambda
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   ├── list-urls/                      # List URLs Lambda
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   └── delete-url/                     # Delete URL Lambda
│       ├── lambda_function.py
│       └── requirements.txt
├── tests/                              # Test files
│   ├── test_create_url.py              # Create function tests
│   ├── test_get_url.py                 # Get function tests
│   ├── test_list_urls.py               # List function tests
│   ├── test_delete_url.py              # Delete function tests
│   └── requirements.txt                # pytest, pytest-cov
├── cloudformation/                     # SAM CloudFormation
│   └── template.yaml                   # Infrastructure definition
├── .gitignore                          # Git ignore patterns
├── .python-version                     # pyenv Python version
└── README.md                           # This file
```

## Troubleshooting

### Common Issues

#### 1. SAM Build Fails

**Problem**: `sam build` fails with dependency errors

**Solution**:
```bash
# Ensure each Lambda has requirements.txt
ls src/*/requirements.txt

# Manually install dependencies to test
cd src/create-url
pip install -r requirements.txt
```

#### 2. Deployment Permission Errors

**Problem**: IAM permission denied during deployment

**Solution**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Ensure your IAM user/role has permissions for:
# - CloudFormation stack operations
# - Lambda function creation
# - DynamoDB table creation
# - IAM role creation
# - CloudWatch Logs creation
```

#### 3. Function URL Not Working

**Problem**: 403 Forbidden or connection timeout

**Solution**:
- Verify Function URL is created: Check CloudFormation Outputs
- Ensure `AuthType: NONE` is set in template
- Check Lambda execution role has DynamoDB permissions
- Review CloudWatch Logs for errors

#### 4. DynamoDB Errors

**Problem**: `ResourceNotFoundException` or throttling errors

**Solution**:
```bash
# Verify table exists
aws dynamodb describe-table \
  --table-name url-shortener-us-east-1-123456789012-url-mappings

# Check table status is ACTIVE
# Verify GSI (OriginalURLIndex) is also ACTIVE
```

#### 5. Tests Failing Locally

**Problem**: pytest fails with import errors

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall test dependencies
pip install -r tests/requirements.txt

# Run tests with verbose output
pytest tests/ -v
```

### Viewing Logs

```bash
# View logs for specific function
sam logs --stack-name url-shortener-stack --name CreateURLFunction --tail

# View logs with CloudWatch Insights
aws logs tail /aws/lambda/url-shortener-us-east-1-123456789012-create-url --follow
```

### Testing Deployed Functions

```bash
# Set environment variables for convenience
export CREATE_URL="https://your-create-function-url.lambda-url.us-east-1.on.aws/"
export GET_URL="https://your-get-function-url.lambda-url.us-east-1.on.aws/"
export LIST_URL="https://your-list-function-url.lambda-url.us-east-1.on.aws/"
export DELETE_URL="https://your-delete-function-url.lambda-url.us-east-1.on.aws/"

# Complete workflow test
# 1. Create a URL
RESPONSE=$(curl -s -X POST $CREATE_URL \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/test"}')
echo $RESPONSE

# Extract short_code from response
SHORT_CODE=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['short_code'])")

# 2. Get the URL by short code
curl -s "${GET_URL}?short_code=${SHORT_CODE}" | python3 -m json.tool

# 3. List all URLs
curl -s $LIST_URL | python3 -m json.tool

# 4. Delete the URL
curl -s -X DELETE "${DELETE_URL}?url=https%3A%2F%2Fexample.com%2Ftest" | python3 -m json.tool
```

## Cleanup

To remove all AWS resources and avoid ongoing charges:

### Option 1: Using SAM CLI

```bash
# Delete the entire stack
sam delete --stack-name url-shortener-stack

# Confirm deletion when prompted
```

### Option 2: Using AWS CLI

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name url-shortener-stack

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name url-shortener-stack
```

### Verify Cleanup

```bash
# Verify stack is deleted
aws cloudformation describe-stacks --stack-name url-shortener-stack
# Should return: "Stack with id url-shortener-stack does not exist"

# Verify DynamoDB table is deleted
aws dynamodb list-tables | grep url-shortener
# Should return no results
```

### Manual Cleanup (if needed)

If automatic cleanup fails:

```bash
# Delete DynamoDB table
aws dynamodb delete-table --table-name url-shortener-us-east-1-123456789012-url-mappings

# Delete Lambda functions
aws lambda delete-function --function-name url-shortener-us-east-1-123456789012-create-url
aws lambda delete-function --function-name url-shortener-us-east-1-123456789012-get-url
aws lambda delete-function --function-name url-shortener-us-east-1-123456789012-list-urls
aws lambda delete-function --function-name url-shortener-us-east-1-123456789012-delete-url

# Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /aws/lambda/url-shortener-us-east-1-123456789012-create-url
aws logs delete-log-group --log-group-name /aws/lambda/url-shortener-us-east-1-123456789012-get-url
aws logs delete-log-group --log-group-name /aws/lambda/url-shortener-us-east-1-123456789012-list-urls
aws logs delete-log-group --log-group-name /aws/lambda/url-shortener-us-east-1-123456789012-delete-url
```

## Cost Considerations

This is a proof-of-concept with minimal costs:

- **Lambda**: Free tier includes 1M requests/month and 400,000 GB-seconds compute
- **DynamoDB**: Pay-per-request pricing, ~$1.25 per million write requests, $0.25 per million read requests
- **CloudWatch Logs**: $0.50 per GB ingested, $0.03 per GB stored
- **Data Transfer**: First 1 GB/month free, then $0.09 per GB

Expected monthly cost for light usage: **< $1**

## Security Considerations

This is a proof-of-concept with **no authentication**. For production use:

- Add API key authentication or AWS IAM authorization
- Implement rate limiting per client
- Add AWS WAF for DDoS protection
- Enable DynamoDB encryption at rest
- Use VPC endpoints for private access
- Add input sanitization for XSS prevention
- Implement request signing for API integrity

## License

This project is a proof-of-concept for educational purposes.

## Support

For issues or questions:
1. Check CloudWatch Logs for error details
2. Review the troubleshooting section above
3. Verify all prerequisites are installed correctly
4. Ensure AWS credentials have appropriate permissions
