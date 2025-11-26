---
inclusion: always
---
# Project Structure

## Directory Organization

```
.
├── .kiro/                              # Kiro configuration and specs
│   ├── specs/url-shortener-api         # Kiro specs for URL shortener API
│   └── steering/                       # AI assistant steering rules
├── .venv/                              # Python virtual environment
├── src/                                # Lambda source code
│   └── {lambda_name}/                  # Individual lambda directories
│       ├── lambda_function.py          # Main lambda handler
│       ├── requirements.txt            # Lambda dependencies
│       └── README.md                   # Lambda documentation
├── tests/                              # Tests
│   └── requirements.txt                # Test dependencies
├── cloudformation/                     # SAM Cloudformation Folder
│   └── template.yaml                   # SAM Cloudformation template
└── README.md                           # Project documentation
