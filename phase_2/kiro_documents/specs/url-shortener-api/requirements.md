# Requirements Document

## Introduction

This document specifies the requirements for a URL Shortener API service proof of concept. The system will provide publicly accessible RESTful API endpoints to create shortened URLs, retrieve original URLs, and track basic usage metrics. The service will be deployed on AWS using serverless architecture (Lambda with Function URLs, DynamoDB) and managed through SAM (Serverless Application Model) CloudFormation templates. This is a proof of concept without authentication or user-specific data.

## Glossary

- **URL Shortener System**: The complete serverless application including Lambda functions with Function URLs and DynamoDB storage
- **Short Code**: A unique alphanumeric identifier consisting of exactly 6 characters that represents a shortened URL
- **Original URL**: The full-length URL that a user wants to shorten
- **Retrieval Service**: The Lambda function that resolves short codes to original URLs and returns them in API responses
- **API Client**: Any application or user making requests to the URL Shortener API
- **DynamoDB Table**: The NoSQL database table storing URL mappings and metadata
- **SAM Template**: The CloudFormation template written in SAM syntax that defines infrastructure
- **Lambda Function URL**: The HTTPS endpoint automatically generated for Lambda functions to handle HTTP requests

## Requirements

### Requirement 1

**User Story:** As an API client, I want to POST a long URL and receive a unique shortened URL back, so that I can share a compact link.

#### Acceptance Criteria

1. WHEN the API Client sends a POST request with a valid HTTP/HTTPS URL in the request body, THE URL Shortener System SHALL generate a unique 6-character alphanumeric Short Code and return the complete shortened URL in a JSON response within 2 seconds
2. THE URL Shortener System SHALL ensure that each generated Short Code is unique and consists of exactly 6 alphanumeric characters
3. THE URL Shortener System SHALL validate that submitted URLs use HTTP or HTTPS protocols
4. THE URL Shortener System SHALL store the mapping between the Short Code and Original URL in the DynamoDB Table with a timestamp
5. THE URL Shortener System SHALL return an error response with status code 400 when the API Client submits an invalid URL format
6. WHEN the API Client submits an Original URL that already exists in the system, THE URL Shortener System SHALL return the existing Short Code rather than creating a duplicate

### Requirement 2

**User Story:** As an API client, I want to retrieve the original URL by submitting a short code or retrieve the short URL by submitting the original URL, so that I can look up either direction of the mapping.

#### Acceptance Criteria

1. WHEN the API Client sends a GET request with a valid Short Code, THE URL Shortener System SHALL retrieve the Original URL from the DynamoDB Table and return it in a JSON response within 1 second
2. WHEN the API Client sends a GET request with a valid Original URL, THE URL Shortener System SHALL retrieve the corresponding Short Code from the DynamoDB Table and return the shortened URL in a JSON response within 1 second
3. THE URL Shortener System SHALL increment the access count for the Short Code in the DynamoDB Table each time a retrieval occurs
4. THE URL Shortener System SHALL include the Original URL, shortened URL, creation timestamp, and access count in the JSON response
5. THE URL Shortener System SHALL return an HTTP 404 error response when the API Client requests a Short Code or Original URL that does not exist
6. THE URL Shortener System SHALL handle at least 100 concurrent retrieval requests without degradation

### Requirement 3

**User Story:** As an API client, I want to list all shortened URLs with their original URLs, so that I can view all mappings in the system.

#### Acceptance Criteria

1. WHEN the API Client sends a GET request to the list endpoint, THE URL Shortener System SHALL return all URL mappings from the DynamoDB Table in a JSON response within 3 seconds
2. THE URL Shortener System SHALL include the Short Code, Original URL, creation timestamp, and access count for each mapping in the response
3. THE URL Shortener System SHALL return an empty list when no URL mappings exist in the system
4. THE URL Shortener System SHALL handle at least 50 concurrent list requests without degradation

### Requirement 4

**User Story:** As an API client, I want to delete a URL mapping by providing the original URL, so that I can remove unwanted shortened URLs from the system.

#### Acceptance Criteria

1. WHEN the API Client sends a DELETE request with a valid Original URL, THE URL Shortener System SHALL remove the corresponding URL mapping from the DynamoDB Table and return a success response within 1 second
2. THE URL Shortener System SHALL return an HTTP 404 error response when the API Client attempts to delete an Original URL that does not exist
3. THE URL Shortener System SHALL return a JSON response confirming the deletion with the deleted Short Code and Original URL
4. THE URL Shortener System SHALL handle at least 50 concurrent delete requests without degradation

### Requirement 5

**User Story:** As a developer, I want to deploy the entire infrastructure using SAM templates, so that I can provision and manage resources consistently across environments.

#### Acceptance Criteria

1. THE URL Shortener System SHALL be defined in a SAM template that includes Lambda functions with Function URLs and DynamoDB Table resources
2. THE SAM Template SHALL specify appropriate IAM roles and policies for Lambda functions to access the DynamoDB Table
3. THE SAM Template SHALL configure Lambda Function URLs with public access (no authentication) for URL creation and retrieval operations
4. THE SAM Template SHALL define DynamoDB Table with appropriate partition key for efficient queries
5. WHEN a developer executes SAM deploy command, THE URL Shortener System SHALL provision all required AWS resources and output the Lambda Function URLs

### Requirement 6

**User Story:** As a system administrator, I want the service to handle errors gracefully and log operations, so that I can monitor and troubleshoot issues effectively.

#### Acceptance Criteria

1. WHEN an error occurs during URL processing, THE URL Shortener System SHALL log the error details to CloudWatch Logs with appropriate severity levels
2. THE URL Shortener System SHALL return structured JSON error responses with descriptive messages and appropriate HTTP status codes
3. THE URL Shortener System SHALL log each API request with timestamp, Short Code, and operation type to CloudWatch Logs
4. WHEN the DynamoDB Table is unavailable, THE URL Shortener System SHALL return an HTTP 503 error response to the API Client

### Requirement 7

**User Story:** As a developer, I want comprehensive documentation explaining how to use and deploy the service, so that I can quickly understand and operate the system.

#### Acceptance Criteria

1. THE URL Shortener System SHALL include a README file that documents all API endpoints with request and response examples
2. THE README file SHALL provide step-by-step deployment instructions using SAM CLI commands
3. THE README file SHALL document all required prerequisites including Python version, AWS CLI, and SAM CLI
4. THE README file SHALL include examples of how to test each API endpoint using curl or similar tools
5. THE README file SHALL document the DynamoDB Table schema and key structure
