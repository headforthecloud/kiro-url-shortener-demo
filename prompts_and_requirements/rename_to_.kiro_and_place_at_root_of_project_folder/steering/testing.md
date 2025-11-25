---
inclusion: always
---

## Python testing
- whenever we create a lambda function, create a pytest test script in the /tests folder
- we will use mocking to test calls to boto3, rather than deploying. We will not use the moto library
- we will ensure we have at least 75% code coverage from the tests
- All tests should pass

## Cloudformation
- we will use cfn-lint to ensure the cloudformation template is correctly formatted. This should be checked once the template creation is complete.
