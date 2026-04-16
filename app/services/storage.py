import boto3
from botocore.config import Config
from app.core.config import settings


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


async def upload_file(file_path: str, r2_key: str, content_type: str = "application/octet-stream") -> str:
    client = get_r2_client()
    client.upload_file(
        file_path,
        settings.R2_BUCKET_NAME,
        r2_key,
        ExtraArgs={"ContentType": content_type}
    )
    return f"{settings.R2_PUBLIC_URL}/{r2_key}"


async def get_signed_url(r2_key: str, expires_in: int = 3600) -> str:
    client = get_r2_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": r2_key},
        ExpiresIn=expires_in,
    )
    return url


async def delete_file(r2_key: str):
    client = get_r2_client()
    client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=r2_key)
