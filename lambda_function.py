import os
import json
import logging
import boto3
import requests
import botocore.auth
import botocore.awsrequest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
GCP_SA_EMAIL = os.environ["GCP_SA_EMAIL"]
WIF_POOL_PROVIDER = os.environ["WIF_POOL_PROVIDER"]
GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# API Endpoints
AWS_STS_ENDPOINT = "https://sts.amazonaws.com"
GCP_STS_ENDPOINT = "https://sts.googleapis.com/v1/token"
GCP_IAM_CREDENTIALS_ENDPOINT = "https://iamcredentials.googleapis.com/v1"
GCS_UPLOAD_ENDPOINT = "https://storage.googleapis.com/upload/storage/v1/b"

# Token and scope constants
TOKEN_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:token-exchange"
REQUESTED_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
SUBJECT_TOKEN_TYPE = "urn:ietf:params:aws:token-type:aws4_request"
GCP_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
GCS_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/devstorage.read_write"

# AWS STS constants
STS_ACTION = "GetCallerIdentity"
STS_VERSION = "2011-06-15"

def get_aws_subject_token():
    """Gets a JWT token from AWS STS for outbound federation"""
    logger.info("Getting AWS JWT token for outbound federation")
    
    sts_client = boto3.client('sts', region_name=AWS_REGION)
    
    response = sts_client.get_web_identity_token(
        Audience=["gcp-storage-access"],
        SigningAlgorithm='RS256'
    )
    
    logger.info("AWS JWT token generated successfully")
    return response['WebIdentityToken']

def exchange_aws_to_gcp_token(subject_token):
    """Exchanges the AWS JWT token for a Google federated token using Workload Identity Federation"""
    logger.info("Exchanging AWS token for GCP federated token")
    logger.info("WIF_POOL_PROVIDER value: %s", WIF_POOL_PROVIDER)
    
    response = requests.post(
        GCP_STS_ENDPOINT,
        json={
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "audience": f"//iam.googleapis.com/{WIF_POOL_PROVIDER}",
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
            "subject_token": subject_token,
            "scope": "https://www.googleapis.com/auth/cloud-platform"
        }
    )
    
    if response.status_code != 200:
        logger.error("GCP STS Error: %s", response.text)
    response.raise_for_status()
    logger.info("Successfully obtained GCP federated token")
    return response.json()["access_token"]

def impersonate_service_account(federated_token):
    """Impersonates the GCP Service Account to obtain an access token for GCS"""
    logger.info(f"Impersonating GCP Service Account: {GCP_SA_EMAIL}")
    response = requests.post(
        f"{GCP_IAM_CREDENTIALS_ENDPOINT}/projects/-/serviceAccounts/"
        f"{GCP_SA_EMAIL}:generateAccessToken",
        headers={
            "Authorization": f"Bearer {federated_token}",
            "Content-Type": "application/json"
        },
        json={
            "scope": [GCS_READ_WRITE_SCOPE]
        }
    )
    response.raise_for_status()
    logger.info("Successfully impersonated service account and obtained access token")
    return response.json()["accessToken"]

def upload_to_gcs(gcp_access_token):
    """Uploads a simple text file to the specified GCS bucket using the GCP access token"""
    logger.info(f"Uploading file to GCS bucket: {GCS_BUCKET_NAME}")
    response = requests.post(
        f"{GCS_UPLOAD_ENDPOINT}/"
        f"{GCS_BUCKET_NAME}/o?uploadType=media&name=output_data.txt",
        headers={
            "Authorization": f"Bearer {gcp_access_token}",
            "Content-Type": "text/plain"
        },
        data=b"Hello from AWS outbound federation demo"
    )
    response.raise_for_status()
    logger.info("File uploaded successfully to GCS")

def lambda_handler(event, context):
    logger.info("Lambda function invoked - starting AWS to GCS federation workflow")
    subject_token = get_aws_subject_token()
    federated_token = exchange_aws_to_gcp_token(subject_token)
    gcp_access_token = impersonate_service_account(federated_token)
    upload_to_gcs(gcp_access_token)

    logger.info("Workflow completed successfully")
    return {"statusCode": 200, "body": "Success"}
