# Design Document

## Overview

The URL Shortener API is a serverless proof-of-concept application built on AWS using Python and SAM (Serverless Application Model). The system provides a RESTful API for creating, retrieving, listing, and deleting URL mappings between long URLs and 6-character alphanumeric short codes. The architecture leverages AWS Lambda with Function URLs for compute, DynamoDB for storage, and CloudWatch for logging and monitoring.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    Client[API Client]
    
    CreateFunc[Create Lambda<br/>Function URL]
    GetFunc[Get Lambda<br/>Function URL]
    ListFunc[List Lambda<br/>Function URL]
    DeleteFunc[Delete Lambda<br/>Function URL]
    
    DDB[(DynamoDB Table<br/>URLMappings)]
    CW[CloudWatch Logs]
    
    Client -->|POST /create| CreateFunc
    Client -->|GET /get| GetFunc
    Client -->|GET /list| ListFunc
    Client -->|DELETE /delete| DeleteFunc
    
    CreateFunc --> DDB
    GetFunc --> DDB
    ListFunc --> DDB
    DeleteFunc --> DDB
    
    CreateFunc --> CW
    GetFunc --> CW
    ListFunc --> CW
    DeleteFunc --> CW
```

### Technology Stack

- **Language**: Python 3.11+
- **Infrastructure as Code**: AWS SAM (Serverless Application Model)
- **Compute**: AWS Lambda with Function URLs
- **Storage**: Amazon DynamoDB
- **Logging**: Amazon CloudWatch Logs
- **Deployment**: SAM CLI

### Design Decisions

1. **Lambda Function URLs over API Gateway**: Simplified architecture for proof of concept, reducing complexity and cost while providing public HTTPS endpoints
2. **Separate Lambda functions per operation**: Clear separation of concerns, easier to maintain and scale independently
3. **DynamoDB single-table design**: Cost-effective and performant for the scale of this POC
4. **No authentication**: Public access for proof of concept simplicity
5. **6-character alphanumeric codes**: Provides 56.8 billion possible combinations (62^6), sufficient for POC scale

## Components and Interfaces

### Lambda Functions

#### 1. Create URL Function
- **Purpose**: Generate short codes and store URL mappings
- **HTTP Method**: POST
- **Request Body**:
```json
{
  "url": "https://example.com/very/long/url"
}
```
- **Response** (201 Created):
```json
{
  "short_code": "abc123",
  "short_url": "https://<function-url>/abc123",
  "original_url": "https://example.com/very/long/url",
  "created_at": "2025-11-16T10:30:00Z"
}
```
- **Error Response** (400 Bad Request):
```json
{
  "error": "Invalid URL format",
  "message": "URL must use HTTP or HTTPS protocol"
}
```

#### 2. Get URL Function
- **Purpose**: Retrieve URL mappings by short code or original URL
- **HTTP Method**: GET
- **Query Parameters**: 
  - `short_code`: The 6-character code (e.g., `?short_code=abc123`)
  - `url`: The original URL (e.g., `?url=https://example.com/...`)
- **Response** (200 OK):
```json
{
  "short_code": "abc123",
  "short_url": "https://<function-url>/abc123",
  "original_url": "https://example.com/very/long/url",
  "created_at": "2025-11-16T10:30:00Z",
  "access_count": 42
}
```
- **Error Response** (404 Not Found):
```json
{
  "error": "Not found",
  "message": "No mapping found for the provided identifier"
}
```

#### 3. List URLs Function
- **Purpose**: Retrieve all URL mappings
- **HTTP Method**: GET
- **Response** (200 OK):
```json
{
  "urls": [
    {
      "short_code": "abc123",
      "short_url": "https://<function-url>/abc123",
      "original_url": "https://example.com/very/long/url",
      "created_at": "2025-11-16T10:30:00Z",
      "access_count": 42
    }
  ],
  "count": 1
}
```

#### 4. Delete URL Function
- **Purpose**: Remove URL mappings by original URL
- **HTTP Method**: DELETE
- **Query Parameters**: `url` (the original URL to delete)
- **Response** (200 OK):
```json
{
  "message": "URL mapping deleted successfully",
  "short_code": "abc123",
  "original_url": "https://example.com/very/long/url"
}
```
- **Error Response** (404 Not Found):
```json
{
  "error": "Not found",
  "message": "No mapping found for the provided URL"
}
```

### Shared Components

#### URL Validator Module
- Validates URL format (HTTP/HTTPS only)
- Checks URL structure and protocol
- Returns validation errors with descriptive messages

#### Short Code Generator Module
- Generates random 6-character alphanumeric codes
- Uses characters: a-z, A-Z, 0-9 (62 possible characters)
- Implements collision detection and retry logic
- Maximum retry attempts: 5

#### DynamoDB Client Module
- Abstracts DynamoDB operations
- Handles connection management
- Implements error handling and retries
- Provides consistent interface for all Lambda functions

#### Logger Module
- Structured logging to CloudWatch
- Includes request context (timestamp, operation, identifiers)
- Configurable log levels
- Consistent log format across all functions

## Data Models

### DynamoDB Table: URLMappings

**Table Structure**:
- **Table Name**: `URLMappings`
- **Partition Key**: `short_code` (String)
- **Global Secondary Index**: `OriginalURLIndex`
  - **Partition Key**: `original_url` (String)

**Item Schema**:
```json
{
  "short_code": "abc123",
  "original_url": "https://example.com/very/long/url",
  "created_at": "2025-11-16T10:30:00Z",
  "access_count": 42,
  "ttl": 1735689000
}
```

**Attributes**:
- `short_code` (String, Required): The unique 6-character identifier
- `original_url` (String, Required): The full URL to be shortened
- `created_at` (String, Required): ISO 8601 timestamp of creation
- `access_count` (Number, Required): Number of times the mapping has been retrieved
- `ttl` (Number, Optional): Unix timestamp for automatic item expiration (not implemented in POC)

**Access Patterns**:
1. Get by short code: Query using partition key
2. Get by original URL: Query using GSI
3. Check if URL exists: Query using GSI
4. List all URLs: Scan operation
5. Delete by original URL: Query GSI, then delete by short code

## Error Handling

### Error Categories

1. **Client Errors (4xx)**:
   - 400 Bad Request: Invalid URL format, missing required fields
   - 404 Not Found: Short code or URL not found in database
   - 409 Conflict: Duplicate short code generation failure after retries

2. **Server Errors (5xx)**:
   - 500 Internal Server Error: Unexpected errors, code exceptions
   - 503 Service Unavailable: DynamoDB unavailable or throttled

### Error Response Format

All errors return consistent JSON structure:
```json
{
  "error": "Error category",
  "message": "Detailed error description",
  "request_id": "lambda-request-id"
}
```

### Retry Logic

- **Short code generation**: Up to 5 retries on collision
- **DynamoDB operations**: AWS SDK default retry with exponential backoff
- **Lambda invocations**: No automatic retry (client responsibility)

### Logging Strategy

- **INFO**: Successful operations, request/response summaries
- **WARNING**: Retry attempts, validation failures
- **ERROR**: DynamoDB errors, unexpected exceptions
- **DEBUG**: Detailed request/response data (disabled in production)

## Testing Strategy

### Unit Testing

**Scope**: Individual functions and modules in isolation

**Test Cases**:
1. **URL Validator**:
   - Valid HTTP/HTTPS URLs
   - Invalid protocols (ftp, file, etc.)
   - Malformed URLs
   - Empty or null inputs

2. **Short Code Generator**:
   - Generates 6-character codes
   - Uses only alphanumeric characters
   - Handles collision detection
   - Respects retry limits

3. **DynamoDB Client**:
   - Successful CRUD operations
   - Error handling for missing items
   - Connection error handling
   - Proper data serialization

### Integration Testing

**Scope**: Lambda functions with DynamoDB

**Test Cases**:
1. **Create Function**:
   - Create new URL mapping
   - Return existing mapping for duplicate URL
   - Handle invalid URL input
   - Verify DynamoDB item creation

2. **Get Function**:
   - Retrieve by short code
   - Retrieve by original URL
   - Handle non-existent identifiers
   - Verify access count increment

3. **List Function**:
   - Return all mappings
   - Handle empty table
   - Verify response format

4. **Delete Function**:
   - Delete existing mapping
   - Handle non-existent URL
   - Verify DynamoDB item deletion

### Manual Testing

**Scope**: End-to-end API testing via curl/Postman

**Test Scenarios**:
1. Complete workflow: Create → Get → List → Delete
2. Error scenarios: Invalid inputs, non-existent resources
3. Concurrent requests: Multiple creates, gets
4. Edge cases: Very long URLs, special characters

## Deployment Architecture

### SAM Template Structure

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  # DynamoDB Table
  URLMappingsTable:
    Type: AWS::DynamoDB::Table
    
  # Lambda Functions
  CreateURLFunction:
    Type: AWS::Serverless::Function
    
  GetURLFunction:
    Type: AWS::Serverless::Function
    
  ListURLsFunction:
    Type: AWS::Serverless::Function
    
  DeleteURLFunction:
    Type: AWS::Serverless::Function

Outputs:
  CreateURLEndpoint:
    Description: Create URL Function URL
    
  GetURLEndpoint:
    Description: Get URL Function URL
    
  ListURLsEndpoint:
    Description: List URLs Function URL
    
  DeleteURLEndpoint:
    Description: Delete URL Function URL
```

### IAM Permissions

Each Lambda function requires:
- `dynamodb:PutItem` (Create function)
- `dynamodb:GetItem` (Get function)
- `dynamodb:Query` (Get, Delete functions)
- `dynamodb:Scan` (List function)
- `dynamodb:DeleteItem` (Delete function)
- `dynamodb:UpdateItem` (Get function for access count)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` (All functions)

### Environment Variables

Each Lambda function receives:
- `TABLE_NAME`: DynamoDB table name
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, etc.)
- `AWS_REGION`: AWS region for DynamoDB client

## Performance Considerations

### Scalability

- **Lambda concurrency**: Default account limits (1000 concurrent executions)
- **DynamoDB capacity**: On-demand billing mode for automatic scaling
- **Function URLs**: No throttling limits beyond Lambda concurrency

### Latency Targets

- Create operation: < 2 seconds (includes short code generation and DynamoDB write)
- Get operation: < 1 second (single DynamoDB query)
- List operation: < 3 seconds (full table scan)
- Delete operation: < 1 second (GSI query + delete)

### Optimization Strategies

1. **Connection reuse**: Initialize DynamoDB client outside handler for connection pooling
2. **Minimal dependencies**: Keep Lambda package size small for faster cold starts
3. **Efficient queries**: Use partition key and GSI for O(1) lookups
4. **Batch operations**: Not implemented in POC, but could batch list operations for large datasets

## Security Considerations

### Current Implementation (POC)

- **No authentication**: Function URLs are publicly accessible
- **No authorization**: All operations available to all clients
- **No rate limiting**: Relies on AWS Lambda throttling
- **No input sanitization**: Basic URL validation only

### Production Recommendations

- Implement API key authentication
- Add AWS WAF for DDoS protection
- Enable CloudWatch alarms for anomalous activity
- Add request signing for API integrity
- Implement rate limiting per client
- Add input sanitization for XSS prevention
- Enable DynamoDB encryption at rest
- Use VPC endpoints for private access

## Monitoring and Observability

### CloudWatch Metrics

- Lambda invocation count, duration, errors
- DynamoDB read/write capacity units
- Lambda concurrent executions
- Function URL request count

### CloudWatch Logs

- Structured JSON logs from all Lambda functions
- Request/response logging
- Error stack traces
- Performance timing data

### Alarms (Recommended)

- Lambda error rate > 5%
- Lambda duration > 10 seconds
- DynamoDB throttled requests > 0
- Lambda concurrent executions > 800

## Future Enhancements

1. **Custom short codes**: Allow users to specify custom short codes
2. **Expiration**: Implement TTL for automatic URL expiration
3. **Analytics**: Track click-through rates, geographic data
4. **Batch operations**: Create/delete multiple URLs in single request
5. **Caching**: Add CloudFront or ElastiCache for frequently accessed URLs
6. **Authentication**: Add API key or OAuth support
7. **Rate limiting**: Implement per-client rate limits
8. **URL validation**: Check if destination URLs are reachable
