# AWS Bedrock Integration for HerbariumScribe

This guide explains how to set up and use AWS Bedrock models with the HerbariumScribe transcription application.

## Prerequisites

1. An AWS account with access to AWS Bedrock service
2. AWS credentials configured on your machine
3. Python 3.9+ with required dependencies installed

## Setup Steps

### 1. Configure AWS Credentials

Ensure your AWS credentials are properly configured:

```bash
# Option 1: Using AWS CLI
aws configure

# Option 2: Create or edit ~/.aws/credentials file
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
aws_region = us-east-1  # or your preferred region
```

### 2. Run the Bedrock Setup Script

```bash
python setup_bedrock.py
```

This script will:
- Create necessary directories
- Install required dependencies
- Test connection to AWS Bedrock
- Retrieve available models
- Test vision models for compatibility

### 3. Test Bedrock Models

When prompted by the setup script, choose to run the model tester:

```
Do you want to run the model tester to test vision models? (y/n): y
```

The model tester will:
- Test each available vision model with a sample image
- Record which models successfully process images
- Save test results to `test_results` directory
- Update `vision_model_info.json` with test results

## Using Bedrock Models in Transcriber

1. Launch the transcriber application:
   ```bash
   python transcriber.py
   ```

2. Enter your username and select "Process New Images"

3. Select a prompt template

4. In the LLM selection dropdown, you'll see Bedrock models that passed the image test
   - Models are prefixed with "bedrock-" followed by their model ID
   - Only models that successfully processed images in testing will be shown

5. Select one or more models (you can use both Bedrock and non-Bedrock models)

6. No API key is required for Bedrock models as they use your AWS credentials

7. Continue with image selection and processing as normal

## Supported Bedrock Models

The following Bedrock models have been tested for image processing:

- Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
- Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20240620-v1:0`)
- Claude 3.7 Sonnet (`anthropic.claude-3-7-sonnet-20250219-v1:0`)
- Amazon Nova models (`amazon.nova-*`)

Note: Model availability may vary based on your AWS region and account permissions.

## Troubleshooting

### Model Not Appearing in Selection

- Ensure the model passed the image test (check `test_results` directory)
- Verify your AWS credentials have access to the model
- Run the model tester again to update the model information

### Processing Errors

- Check AWS CloudTrail logs for any permission issues
- Ensure your AWS account has the necessary quotas for the selected models
- Verify the model supports image processing capabilities

## Additional Information

- Bedrock model results are saved in the same format as other models
- Cost information is tracked and displayed for Bedrock models
- For more details on AWS Bedrock, visit the [AWS Bedrock documentation](https://docs.aws.amazon.com/bedrock/)