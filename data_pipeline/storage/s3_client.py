import boto3
from botocore.client import Config as BotoConfig
from data_pipeline.config import Config

def get_s3_client():
    """
    Creates and returns a boto3 client connected to MinIO or S3.
    """
    return boto3.client(
        "s3",
        endpoint_url=Config.S3_ENDPOINT_URL,
        aws_access_key_id=Config.S3_ACCESS_KEY,
        aws_secret_access_key=Config.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1"
    )

def init_buckets():
    """
    Checks if buckets exist, if not, creates them.
    """
    s3 = get_s3_client()
    for bucket_name in [Config.BRONZE_BUCKET, Config.SILVER_BUCKET, Config.GOLD_BUCKET]:
        try:
            s3.head_bucket(Bucket=bucket_name)
            print(f"Bucket já existe: {bucket_name}")
        except Exception:
            print(f"Criando bucket: {bucket_name}")
            try:
                s3.create_bucket(Bucket=bucket_name)
            except Exception as e:
                print(f"Erro ao criar bucket {bucket_name}: {e}")
