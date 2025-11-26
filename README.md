# Kiro & Spec Based Development
This repository contains code and documents produced as part of my demonstration on Specification Based Development using Kiro, specifically the session recorded at https://youtu.be/Sa1FkCPVwzI

The demo is divided into 4 parts
1. [Vibe Based Coding](#phase-1---vibe-based-coding) - a quick review of the 'traditional' approach to development using AI Coding Assistants,
1. [Specification Based Coding](#phase-2---specification-based-coding) - a demonstration of how Kiro works with a spec-based approach,
1. [Using Steering Documents](#phase-3---specification-based-coding-with-steering-documents) - this expands on the previous section, looking to how we can use Steering Documents to implement best practices and standards within our projects,
1. [Final Results](#phase-4---final-results) - the code generated in [Phase 3](#phase-3---specification-based-coding-with-steering-documents)

The specific items in the repository are explained below:

## Phase 1 - Vibe Based Coding
*(video timecode 00:40)*

This was a simple demonstration - it shows the use of two prompts to generate code
1. create a python function that generates a 6 character for an input string
1. convert the code to a aws lambda function

step 1 generates some straightforward Python code, which is then converted to a lambda function using the second prompt

## Phase 2 - Specification Based Coding
*(video timecode 02:30)*
In this section, we looked at generating a specification based on a set of [prompts](./phase_2/spec_prompts.md).

Selecting specification based mode, and entering the prompts will lead to the creation of the 3 spec documents.

The resulting [requirements](./phase_2/kiro_documents/specs/url-shortener-api/requirements.md), [design](./phase_2/kiro_documents/specs/url-shortener-api/design.md), and [task list](./phase_2/kiro_documents/specs/url-shortener-api/tasks.md) can be copied to a folder under `.kiro/specs`, for example `.kiro/specs/url-shortener-api`. 

## Phase 3 - Specification Based Coding with Steering Documents
*(video timecode 08:30)*
This section builds upon the idea of specification based development by introducing _steering documents_. These are used to describe any best practices / engineering standards you'd like to introduce to your products.

There are 3 steering documents:
* [structure](./phase_3/kiro_documents/steering/structure.md) - this describes the file and folder structure we'd like to use
* [tech](./phase_3/kiro_documents/steering/tech.md) - this document describes your tech stack i.e. programming language, infrastructure as code tools, required libraries, local development setup etc.
* [testing](./phase_3/kiro_documents/steering/testing.md) - this describes any testing approach.

All steering documents, but the Kiro documentation suggests 3 standard ones - see https://kiro.dev/docs/steering/#foundational-steering-files for more info; we use the structure and tech documents suggested, and add the testing document.

With this in place, and the 3 spec documents from [phase 2](#phase-2---specification-based-coding), we can prompt Kiro with a prompt similar to:

>  using the steering documents in `<insert_folder_name>`, review the specification, design and tasks documents and make any required changes to ensure they take the steering documents into account'

This will lead to an updated set of specification documents - examples can be found [here](./phase_3/kiro_documents/specs/url-shortener-api/).

## Phase 4 - Final Results
*(video timecode 10:55)*
I've included the code generated in the demo - this is split into 3 parts:
1. The Python code used to generate the lambdas for the API
1. The unit tests that can be used to validate the code from 1.
1. The CloudFormation that can be used to deploy the results into an AWS account for testing