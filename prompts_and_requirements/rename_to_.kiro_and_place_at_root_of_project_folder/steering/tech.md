---
inclusion: always
---

## Local Development
- We use pyenv to manage python versions
- Every project should have a .venv environment configured for Python 3.11
- This venv environment should be used when starting terminals
- We should be able to run python tests locally

## Naming conventions
- We use snake_case for all variables and functions
- The cloudformation should have a parameter called project name.
- All resources created should using the naming convention {project_name}-{aws_region}-{aws_account_id} followed by an appropriate resource name

## AWS Resources
- create a unique cloudwatch log group for each lambda. The log groups will share a common period for log retention, specified by a cloudformation parameter
- we should use the cheapest configuration available
- we are building an MVP - use YAGNI principles
- rather than using an API gateway, use lambda function urls

