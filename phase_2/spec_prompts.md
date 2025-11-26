# Prompts for spec based development
These are the prompts I use when generating the spec

```
I want to build an API based url shortener, written in python, and using SAM cloudformation templates for infrastructure as code. The product will be deployed in AWS using serverless technology
just use lambda function urls rather than api gateway

do not perform any redirects, just return the long or short urls as requested

this is just a proof of concept, there will be no authentication or user specific data

users will be able to POST a long url to be shortened, and get a unique shortened url back

the shortened urls should be unique and consist of 6 alphanumeric characters

users will be able to list all urls including the long and short versions

users should be able to retrieve the long version by submitting the short version and vice versa

users should be able to delete a specific URL by providing the long url

when errors occur they should generate the appropriate http status code and message

as the application is built, generate comprehensive documentation stored in a README file explaining how to use and deploy the service
```
