import os
import json
import boto3
import requests
import botocore.auth
import botocore.awsrequest

GCP_SA_EMAIL = os.environ["GCP_SA_EMAIL"]
WIF_POOL_PROVIDER = os.environ["WIF_POOL_PROVIDER"]
GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

def get_aws_subject_token():
    session = boto3.session.Session()
    credentials = session.get_credentials().get_frozen_credentials()

    request = botocore.awsrequest.AWSRequest(
        method="POST",
        url="https://sts.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
        headers={"Host": "sts.amazonaws.com"},
        data=""
    )

    signer = botocore.auth.SigV4Auth(credentials, "sts", AWS_REGION)
    signer.add_auth(request)

    return json.dumps({
        "url": request.url,
        "method": request.method,
        "headers": dict(request.headers),
        "body": ""
    })

def exchange_aws_to_gcp_token(subject_token):
    response = requests.post(
        "https://sts.googleapis.com/v1/token",
        json={
            "grantType": "urn:ietf:params:oauth:grant-type:token-exchange",
            "audience": f"//iam.googleapis.com/{WIF_POOL_PROVIDER}",
            "requestedTokenType": "urn:ietf:params:oauth:token-type:access_token",
            "subjectTokenType": "urn:ietf:params:aws:token-type:aws4_request",
            "subjectToken": subject_token,
            "scope": "https://www.googleapis.com/auth/cloud-platform"
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]

def impersonate_service_account(federated_token):
    response = requests.post(
        f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
        f"{GCP_SA_EMAIL}:generateAccessToken",
        headers={
            "Authorization": f"Bearer {federated_token}",
            "Content-Type": "application/json"
        },
        json={
            "scope": ["https://www.googleapis.com/auth/devstorage.read_write"]
        }
    )
    response.raise_for_status()
    return response.json()["accessToken"]

def upload_to_gcs(gcp_access_token):
    response = requests.post(
        f"https://storage.googleapis.com/upload/storage/v1/b/"
        f"{GCS_BUCKET_NAME}/o?uploadType=media&name=output_data.txt",
        headers={
            "Authorization": f"Bearer {gcp_access_token}",
            "Content-Type": "text/plain"
        },
        data=b"Hello from AWS outbound federation demo"
    )
    response.raise_for_status()

def lambda_handler(event, context):
    subject_token = get_aws_subject_token()
    federated_token = exchange_aws_to_gcp_token(subject_token)
    gcp_access_token = impersonate_service_account(federated_token)
    upload_to_gcs(gcp_access_token)

    return {"statusCode": 200, "body": "Success"}
