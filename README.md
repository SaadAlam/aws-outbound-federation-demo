# AWS Outbound Federation Demo: Upload to GCS from Lambda

This repository demonstrates how to upload a file from an AWS Lambda function to a Google Cloud Storage (GCS) bucket using AWS outbound identity federation (Workload Identity Federation, WIF).

It is intended as a reference example for developers looking to integrate AWS Lambda with GCP services without storing long-lived credentials.

---

## Features

- AWS Lambda function in Python 3.12
- Outbound authentication using AWS Workload Identity Federation (WIF)
- Dynamic GCP access token generation from Lambda role credentials
- Upload files directly to a GCS bucket
- Minimal dependencies: boto3, botocore, requests, python-dotenv (optional for local testing)

---

## Project Structure

    ```
    aws-outbound-federation-demo/
    ├─ lambda_function.py    # Main Lambda code
    ├─ requirements.txt      # Python dependencies
    ├─ .env.example          # Sample environment variables for local testing
    ├─ .gitignore            # Ignore local environment and Python cache
    ├─ README.md             # Project documentation
    ├─ template.yaml         # AWS SAM template for deployment
    ```

---

## Prerequisites

1. AWS account with permissions to create Lambda and IAM roles
2. GCP project with a Service Account having:
   - roles/storage.objectCreator or roles/storage.admin on the target bucket
3. Workload Identity Federation configured in GCP:
   - Create a Workload Identity Pool
   - Create a provider for AWS
   - Map google.subject to the AWS role ARN your Lambda will assume
   - Grant the Service Account impersonation permissions

---

## Environment Variables

Set the following environment variables in Lambda or locally for testing:

| Variable | Description |
|---------:|-------------|
| GCP_SA_EMAIL | GCP Service Account email (target) |
| WIF_POOL_PROVIDER | Full path to GCP WIF provider (e.g., projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/aws-lambda-pool/providers/aws-sts-provider) |
| GCS_BUCKET_NAME | GCS bucket name to upload the file |
| AWS_REGION | AWS region (default: us-east-1) |

> For local testing, you can create a `.env` file based on `.env.example`.

---

## Deployment (Using AWS SAM)

1) Install SAM CLI: [Install SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

2) Build and deploy:

    ```bash
    sam build
    sam deploy --guided
    ```

Provide the parameter values when prompted (GCP Service Account, WIF provider, bucket name).

Note: Default AWS region is us-east-1.

Once deployed, you can invoke your Lambda using the AWS console or CLI.

---

## Getting Started (Example)

After deployment, invoke the Lambda function:

    ```bash
    aws lambda invoke \
      --function-name aws-outbound-federation-demo \
      output.json
    ```

This will upload a file named `output_data.txt` to your configured GCS bucket.

Check your GCS bucket to confirm the file is uploaded successfully.

---

## Running Locally (Optional)

To run locally:

Install Python dependencies:

    ```bash
    pip install -r requirements.txt
    ```

Set environment variables using `.env` or your shell.

Run:

    ```bash
    python lambda_function.py
    ```

> Note: Local runs require your AWS credentials to have access to the role mapped in GCP WIF.

---

## Key Concepts Demonstrated

- AWS Outbound Federation: Authenticate to GCP using Lambda role without storing credentials
- Token Exchange: Exchange AWS-signed JWT for GCP access token via Google STS
- Service Account Impersonation: Temporary GCP credentials scoped to the bucket
- Cross-cloud Integration: Secure interaction with GCP from AWS Lambda

---

## Dependencies

- boto3 – AWS SDK for Python
- botocore – Core AWS functionality for signing requests
- requests – HTTP requests to Google APIs
- python-dotenv – Optional, for local development

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).