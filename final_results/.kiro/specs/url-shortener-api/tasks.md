# Implementation Plan

- [x] 1. Set up project structure and Python environment
  - Create directory structure: src/, tests/, cloudformation/
  - Create .venv with Python 3.13 using pyenv
  - Create tests/requirements.txt with pytest, pytest-cov, and boto3 mocking dependencies
  - Create .gitignore for Python and AWS artifacts
  - _Requirements: 5.1, 5.2_

- [x] 2. Create CloudFormation template foundation
  - Create cloudformation/template.yaml with Parameters section (ProjectName, LogRetentionDays, AWSRegion, AWSAccountId)
  - Define DynamoDB table with partition key (short_code) and GSI on original_url
  - Set billing mode to PAY_PER_REQUEST for cost optimization
  - Use naming convention {project_name}-{aws_region}-{aws_account_id} for all resources (snake_case)
  - _Requirements: 5.1, 5.4_

- [x] 3. Implement Create URL Lambda function
- [x] 3.1 Create Lambda handler and utilities
  - Create src/create-url/ directory with lambda_function.py
  - Implement URL validation (HTTP/HTTPS only)
  - Implement 6-character alphanumeric short code generator with collision detection (max 5 retries)
  - Implement DynamoDB operations: check existing URL via GSI, put new item
  - Parse POST request body and return JSON response with short_code, short_url, original_url, created_at
  - Add error handling for invalid URLs (400), DynamoDB errors (503), collision failures (409)
  - Implement structured logging with CloudWatch integration
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 6.1, 6.2, 6.3, 6.4_

- [x] 3.2 Add Create function to CloudFormation template
  - Define Lambda function resource with Python 3.13 runtime
  - Configure Function URL with AuthType: NONE
  - Create dedicated CloudWatch log group with retention parameter
  - Set environment variables: TABLE_NAME, LOG_LEVEL
  - Define IAM role with DynamoDB PutItem, Query permissions and CloudWatch Logs permissions
  - Add function URL to Outputs section
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [x] 3.3 Create src/create-url/requirements.txt
  - Add boto3 dependency
  - _Requirements: 5.1_

- [x] 3.4 Write pytest tests for Create function
  - Create tests/test_create_url.py with mocked boto3 calls (no moto library)
  - Test successful URL creation, duplicate URL handling, invalid URL format
  - Test collision detection and retry logic
  - Test error scenarios (DynamoDB errors, validation failures)
  - Achieve 75% code coverage minimum
  - All tests must pass
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6_

- [x] 4. Implement Get URL Lambda function
- [x] 4.1 Create Lambda handler
  - Create src/get-url/ directory with lambda_function.py
  - Parse GET request query parameters (short_code or url)
  - Query DynamoDB by short_code (partition key) or original_url (GSI)
  - Increment access_count using UpdateItem with atomic counter
  - Return JSON response with all mapping details
  - Add error handling for missing parameters (400), not found (404), DynamoDB errors (503)
  - Implement structured logging
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 6.1, 6.2, 6.4_

- [x] 4.2 Add Get function to CloudFormation template
  - Define Lambda function resource with Python 3.13 runtime
  - Configure Function URL with AuthType: NONE
  - Create dedicated CloudWatch log group with retention parameter
  - Set environment variables: TABLE_NAME, LOG_LEVEL
  - Define IAM role with DynamoDB GetItem, Query, UpdateItem permissions and CloudWatch Logs permissions
  - Add function URL to Outputs section
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [x] 4.3 Create src/get-url/requirements.txt
  - Add boto3 dependency
  - _Requirements: 5.1_

- [x] 4.4 Write pytest tests for Get function
  - Create tests/test_get_url.py with mocked boto3 calls (no moto library)
  - Test retrieval by short_code and by original_url
  - Test access_count increment
  - Test error scenarios (missing parameters, not found, DynamoDB errors)
  - Achieve 75% code coverage minimum
  - All tests must pass
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. Implement List URLs Lambda function
- [x] 5.1 Create Lambda handler
  - Create src/list-urls/ directory with lambda_function.py
  - Perform DynamoDB Scan operation
  - Handle empty table (return empty list)
  - Format response with urls array and count
  - Add error handling for DynamoDB errors (503)
  - Implement structured logging
  - _Requirements: 3.1, 3.2, 3.3, 6.1, 6.2, 6.4_

- [x] 5.2 Add List function to CloudFormation template
  - Define Lambda function resource with Python 3.13 runtime
  - Configure Function URL with AuthType: NONE
  - Create dedicated CloudWatch log group with retention parameter
  - Set environment variables: TABLE_NAME, LOG_LEVEL
  - Define IAM role with DynamoDB Scan permissions and CloudWatch Logs permissions
  - Add function URL to Outputs section
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [x] 5.3 Create src/list-urls/requirements.txt
  - Add boto3 dependency
  - _Requirements: 5.1_

- [x] 5.4 Write pytest tests for List function
  - Create tests/test_list_urls.py with mocked boto3 calls (no moto library)
  - Test listing with multiple items and empty table
  - Test error scenarios (DynamoDB errors)
  - Achieve 75% code coverage minimum
  - All tests must pass
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 6. Implement Delete URL Lambda function
- [x] 6.1 Create Lambda handler
  - Create src/delete-url/ directory with lambda_function.py
  - Parse DELETE request query parameter (url)
  - Query DynamoDB GSI to find short_code for original_url
  - Delete item from DynamoDB using short_code
  - Return JSON response confirming deletion
  - Add error handling for missing parameter (400), not found (404), DynamoDB errors (503)
  - Implement structured logging
  - _Requirements: 4.1, 4.2, 4.3, 6.1, 6.2, 6.4_

- [x] 6.2 Add Delete function to CloudFormation template
  - Define Lambda function resource with Python 3.13 runtime
  - Configure Function URL with AuthType: NONE
  - Create dedicated CloudWatch log group with retention parameter
  - Set environment variables: TABLE_NAME, LOG_LEVEL
  - Define IAM role with DynamoDB Query, DeleteItem permissions and CloudWatch Logs permissions
  - Add function URL to Outputs section
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [x] 6.3 Create src/delete-url/requirements.txt
  - Add boto3 dependency
  - _Requirements: 5.1_

- [x] 6.4 Write pytest tests for Delete function
  - Create tests/test_delete_url.py with mocked boto3 calls (no moto library)
  - Test successful deletion and not found scenarios
  - Test error scenarios (missing parameter, DynamoDB errors)
  - Achieve 75% code coverage minimum
  - All tests must pass
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 7. Validate CloudFormation template
  - Install cfn-lint in test environment
  - Run cfn-lint on cloudformation/template.yaml
  - Fix any validation errors or warnings
  - _Requirements: 5.1_

- [x] 8. Create comprehensive README documentation
  - Document prerequisites (Python 3.13, pyenv, AWS CLI, SAM CLI)
  - Document local development setup (.venv creation, running tests)
  - Document deployment instructions (sam build, sam deploy --guided)
  - Document all API endpoints with curl examples (Create, Get, List, Delete)
  - Document DynamoDB schema (partition key, GSI, attributes)
  - Include architecture overview and troubleshooting section
  - Document cleanup instructions (sam delete)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
