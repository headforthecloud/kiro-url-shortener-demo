# Implementation Plan

- [ ] 1. Set up project structure and SAM template foundation
  - Create directory structure for Lambda functions and shared modules
  - Initialize SAM template.yaml with basic configuration
  - Create requirements.txt for Python dependencies
  - _Requirements: 5.1, 5.2_

- [ ] 2. Implement shared utility modules
- [ ] 2.1 Create URL validator module
  - Write Python module to validate HTTP/HTTPS URLs
  - Implement protocol checking and format validation
  - Add error message generation for invalid URLs
  - _Requirements: 1.3, 1.5_

- [ ] 2.2 Create short code generator module
  - Implement random 6-character alphanumeric code generation
  - Add collision detection logic with retry mechanism (max 5 attempts)
  - Use characters a-z, A-Z, 0-9 for code generation
  - _Requirements: 1.1, 1.2_

- [ ] 2.3 Create DynamoDB client wrapper module
  - Implement connection management and client initialization
  - Create methods for put_item, get_item, query, scan, delete_item, update_item
  - Add error handling for DynamoDB exceptions
  - _Requirements: 1.4, 2.1, 2.2, 3.1, 4.1, 6.4_

- [ ] 2.4 Create logging utility module
  - Implement structured logging with CloudWatch integration
  - Add log level configuration (INFO, WARNING, ERROR, DEBUG)
  - Create consistent log format with timestamp and context
  - _Requirements: 6.1, 6.3_

- [ ] 3. Define DynamoDB table in SAM template
  - Add DynamoDB table resource with partition key (short_code)
  - Configure Global Secondary Index on original_url
  - Set billing mode to on-demand (PAY_PER_REQUEST)
  - Define attribute definitions for keys
  - _Requirements: 5.1, 5.4_

- [ ] 4. Implement Create URL Lambda function
- [ ] 4.1 Create Lambda handler for URL creation
  - Write handler function to parse POST request body
  - Validate incoming URL using validator module
  - Check if URL already exists using DynamoDB GSI query
  - Generate unique short code using generator module
  - Store mapping in DynamoDB with timestamp and initial access_count
  - Return JSON response with short_code, short_url, original_url, created_at
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

- [ ] 4.2 Add error handling for Create function
  - Handle invalid URL format (400 error)
  - Handle DynamoDB errors (503 error)
  - Handle short code generation failures after retries (409 error)
  - Log all errors to CloudWatch
  - _Requirements: 1.5, 6.1, 6.2, 6.4_

- [ ] 4.3 Configure Create function in SAM template
  - Add Lambda function resource with Python 3.11 runtime
  - Configure Function URL with public access (AuthType: NONE)
  - Set environment variables (TABLE_NAME, LOG_LEVEL)
  - Define IAM policies for DynamoDB PutItem and Query permissions
  - Add CloudWatch Logs permissions
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 5. Implement Get URL Lambda function
- [ ] 5.1 Create Lambda handler for URL retrieval
  - Write handler function to parse GET request query parameters
  - Support both short_code and url query parameters
  - Query DynamoDB by short_code (partition key) or by original_url (GSI)
  - Increment access_count using UpdateItem with atomic counter
  - Return JSON response with all mapping details
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 5.2 Add error handling for Get function
  - Handle missing query parameters (400 error)
  - Handle not found scenarios (404 error)
  - Handle DynamoDB errors (503 error)
  - Log all operations and errors
  - _Requirements: 2.5, 6.1, 6.2, 6.4_

- [ ] 5.3 Configure Get function in SAM template
  - Add Lambda function resource with Python 3.11 runtime
  - Configure Function URL with public access
  - Set environment variables (TABLE_NAME, LOG_LEVEL)
  - Define IAM policies for DynamoDB GetItem, Query, and UpdateItem permissions
  - Add CloudWatch Logs permissions
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 6. Implement List URLs Lambda function
- [ ] 6.1 Create Lambda handler for listing all URLs
  - Write handler function to perform DynamoDB Scan operation
  - Handle empty table scenario (return empty list)
  - Format response with urls array and count
  - Include all mapping details for each item
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 6.2 Add error handling for List function
  - Handle DynamoDB errors (503 error)
  - Log all operations and errors
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 6.3 Configure List function in SAM template
  - Add Lambda function resource with Python 3.11 runtime
  - Configure Function URL with public access
  - Set environment variables (TABLE_NAME, LOG_LEVEL)
  - Define IAM policies for DynamoDB Scan permissions
  - Add CloudWatch Logs permissions
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 7. Implement Delete URL Lambda function
- [ ] 7.1 Create Lambda handler for URL deletion
  - Write handler function to parse DELETE request query parameter (url)
  - Query DynamoDB GSI to find short_code for the original_url
  - Delete item from DynamoDB using short_code
  - Return JSON response confirming deletion with details
  - _Requirements: 4.1, 4.3_

- [ ] 7.2 Add error handling for Delete function
  - Handle missing url parameter (400 error)
  - Handle not found scenarios (404 error)
  - Handle DynamoDB errors (503 error)
  - Log all operations and errors
  - _Requirements: 4.2, 6.1, 6.2, 6.4_

- [ ] 7.3 Configure Delete function in SAM template
  - Add Lambda function resource with Python 3.11 runtime
  - Configure Function URL with public access
  - Set environment variables (TABLE_NAME, LOG_LEVEL)
  - Define IAM policies for DynamoDB Query and DeleteItem permissions
  - Add CloudWatch Logs permissions
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 8. Complete SAM template configuration
  - Add Outputs section with all Function URLs
  - Configure Lambda function memory and timeout settings
  - Add description and metadata to template
  - Ensure all IAM roles follow least privilege principle
  - _Requirements: 5.5_

- [ ] 9. Create comprehensive README documentation
- [ ] 9.1 Document prerequisites and setup
  - List required tools (Python 3.11+, AWS CLI, SAM CLI)
  - Provide installation instructions for each tool
  - Document AWS credentials configuration
  - _Requirements: 7.3_

- [ ] 9.2 Document deployment instructions
  - Write step-by-step SAM build command
  - Write step-by-step SAM deploy command with guided option
  - Explain stack name and region selection
  - Document how to retrieve Function URLs from outputs
  - _Requirements: 7.2_

- [ ] 9.3 Document API endpoints and usage
  - Document Create URL endpoint with curl examples
  - Document Get URL endpoint with curl examples for both query types
  - Document List URLs endpoint with curl examples
  - Document Delete URL endpoint with curl examples
  - Include request and response examples for all endpoints
  - _Requirements: 7.1, 7.4_

- [ ] 9.4 Document DynamoDB schema
  - Document table structure with partition key and GSI
  - Document item attributes and their types
  - Explain access patterns and query methods
  - _Requirements: 7.5_

- [ ] 9.5 Add architecture diagram and additional sections
  - Include architecture overview
  - Add troubleshooting section
  - Document cleanup instructions (deleting the stack)
  - Add example workflows and use cases
  - _Requirements: 7.1_

- [ ] 10. Create samconfig.toml for deployment configuration
  - Configure default deployment parameters
  - Set stack name, region, and capabilities
  - Enable parameter overrides for different environments
  - _Requirements: 5.5_
