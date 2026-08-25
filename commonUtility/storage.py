import hmac
import hashlib
import time
import uuid
import logging
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.urls import reverse
from common.models import S3LikeObject
import boto3

logger = logging.getLogger(__name__)

def compress_image(file_data: bytes, content_type: str, quality=75, max_width=1200) -> tuple[bytes, str]:
    """Compresses image files using PIL to save database space."""
    if not content_type or not content_type.startswith('image/'):
        return file_data, content_type
    
    try:
        img = Image.open(BytesIO(file_data))
        
        # Normalize transparency for JPEG format if needed
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Scale down if exceeds max width
        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            new_size = (max_width, int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        out_io = BytesIO()
        # Convert to JPEG format to save significant space
        img.save(out_io, format='JPEG', quality=quality, optimize=True)
        return out_io.getvalue(), 'image/jpeg'
    except Exception as e:
        logger.warning(f"Image compression failed: {e}")
        # Fallback to original content on processing failures
        return file_data, content_type

class StorageService:
    @staticmethod
    def get_s3_client():
        # Fallback to settings check
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        
        if access_key and secret_key and bucket:
            return boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint,
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'auto')
            )
        return None

    @classmethod
    def upload_file(cls, file_name: str, file_data: bytes, content_type: str, bucket='default') -> S3LikeObject:
        # 1. Compress if it's an image
        processed_data, processed_content_type = compress_image(file_data, content_type)
        size = len(processed_data)
        
        # 2. Check if we should use S3/R2 or local DB
        s3_client = cls.get_s3_client()
        
        # Create key path
        date_prefix = time.strftime('%Y/%m/%d')
        unique_id = uuid.uuid4().hex
        file_ext = file_name.split('.')[-1] if '.' in file_name else 'bin'
        key = f"{date_prefix}/{unique_id}.{file_ext}"
        
        if s3_client:
            bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME')
            logger.info(f"Uploading file to S3 bucket {bucket_name} with key {key}")
            # Upload to S3
            s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=processed_data,
                ContentType=processed_content_type
            )
            # Save record without binary bytes
            obj = S3LikeObject.objects.create(
                bucket=bucket_name,
                key=key,
                content_type=processed_content_type,
                size=size,
                storage_type='s3'
            )
        else:
            logger.info(f"Uploading file to local database bucket {bucket} with key {key}")
            # Save to Database with binary bytes
            obj = S3LikeObject.objects.create(
                bucket=bucket,
                key=key,
                content_type=processed_content_type,
                size=size,
                data=processed_data,
                storage_type='database'
            )
        return obj

    @classmethod
    def generate_signed_url(cls, doc_id: str, expires_in=3600, request=None) -> str:
        obj = S3LikeObject.objects.get(id=doc_id)
        
        if obj.storage_type == 's3':
            s3_client = cls.get_s3_client()
            if s3_client:
                return s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': obj.bucket, 'Key': obj.key},
                    ExpiresIn=expires_in
                )
        
        # Local signature generation
        expires_at = int(time.time()) + expires_in
        message = f"{doc_id}:{expires_at}"
        signature = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        path = reverse('s3-download', kwargs={'doc_id': doc_id})
        query_string = f"?expires={expires_at}&signature={signature}"
        url_path = f"{path}{query_string}"
        
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    @classmethod
    def verify_signature(cls, doc_id: str, expires_at: str, signature: str) -> bool:
        try:
            exp_time = int(expires_at)
        except (ValueError, TypeError):
            return False
            
        if time.time() > exp_time:
            return False
            
        message = f"{doc_id}:{expires_at}"
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)

    @classmethod
    def get_file_data(cls, doc_id: str) -> tuple[bytes, str]:
        obj = S3LikeObject.objects.get(id=doc_id)
        if obj.storage_type == 's3':
            s3_client = cls.get_s3_client()
            if s3_client:
                response = s3_client.get_object(Bucket=obj.bucket, Key=obj.key)
                return response['Body'].read(), obj.content_type
            raise Exception("S3 client not configured in environment")
        return bytes(obj.data), obj.content_type
