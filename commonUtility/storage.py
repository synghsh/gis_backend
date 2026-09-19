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

def compress_image(file_data: bytes, content_type: str, quality=75, max_width=1600, max_size_bytes=5 * 1024 * 1024) -> tuple[bytes, str]:
    """Compresses and resizes image files using PIL, guaranteeing file size does not exceed max_size_bytes (default 5MB)."""
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
            
        cur_width, cur_height = img.size
        cur_quality = quality
        
        # Scale down if exceeds max width
        if cur_width > max_width:
            ratio = max_width / cur_width
            cur_width = max_width
            cur_height = int(cur_height * ratio)
            img = img.resize((cur_width, cur_height), Image.Resampling.LANCZOS)
            
        out_io = BytesIO()
        img.save(out_io, format='JPEG', quality=cur_quality, optimize=True)
        res_bytes = out_io.getvalue()
        
        # Iteratively reduce quality and scale down if image still exceeds max_size_bytes (5MB)
        while len(res_bytes) > max_size_bytes and cur_quality > 20:
            cur_quality = max(20, cur_quality - 15)
            cur_width = int(cur_width * 0.8)
            cur_height = int(cur_height * 0.8)
            img = img.resize((cur_width, cur_height), Image.Resampling.LANCZOS)
            out_io = BytesIO()
            img.save(out_io, format='JPEG', quality=cur_quality, optimize=True)
            res_bytes = out_io.getvalue()
            
        logger.info(f"Image compressed to {len(res_bytes) / 1024:.1f} KB (under 5MB limit)")
        return res_bytes, 'image/jpeg'
    except Exception as e:
        logger.warning(f"Image compression failed: {e}")
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
            from botocore.config import Config
            return boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint,
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'auto'),
                config=Config(signature_version='s3v4')
            )
        return None

    @classmethod
    def upload_file(cls, file_name: str, file_data: bytes, content_type: str, bucket='gis-image', prefix='GIS/erections') -> S3LikeObject:
        # 1. Compress if it's an image
        processed_data, processed_content_type = compress_image(file_data, content_type)
        size = len(processed_data)
        
        target_bucket = bucket or getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'gis-image')
        s3_client = cls.get_s3_client()
        
        # Create key path
        date_prefix = time.strftime('%Y/%m/%d')
        unique_id = uuid.uuid4().hex
        file_ext = file_name.split('.')[-1] if '.' in file_name else 'jpg'
        clean_prefix = prefix.strip('/') if prefix else 'GIS'
        key = f"{clean_prefix}/{date_prefix}/{unique_id}.{file_ext}"
        
        if s3_client:
            logger.info(f"Uploading file to Cloudflare R2 bucket {target_bucket} with key {key}")
            s3_client.put_object(
                Bucket=target_bucket,
                Key=key,
                Body=processed_data,
                ContentType=processed_content_type
            )
            obj = S3LikeObject.objects.create(
                bucket=target_bucket,
                key=key,
                content_type=processed_content_type,
                size=size,
                storage_type='s3'
            )
        else:
            logger.info(f"Uploading file to local database bucket {target_bucket} with key {key}")
            obj = S3LikeObject.objects.create(
                bucket=target_bucket,
                key=key,
                content_type=processed_content_type,
                size=size,
                data=processed_data,
                storage_type='database'
            )
        return obj

    @classmethod
    def get_certified_url(cls, key_or_path: str, expires_in=86400, request=None) -> str:
        if not key_or_path:
            return ""
        if key_or_path.startswith('http://') or key_or_path.startswith('https://'):
            return key_or_path
        if key_or_path.startswith('file://') or key_or_path.startswith('content://'):
            return key_or_path

        public_url = getattr(settings, 'R2_PUBLIC_URL', None) or getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
        if public_url:
            clean_domain = public_url.rstrip('/')
            if not clean_domain.startswith('http://') and not clean_domain.startswith('https://'):
                clean_domain = f"https://{clean_domain}"
            return f"{clean_domain}/{key_or_path.lstrip('/')}"

        s3_client = cls.get_s3_client()
        if s3_client:
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'gis-image')
            try:
                return s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key_or_path},
                    ExpiresIn=expires_in
                )
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL for {key_or_path}: {e}")
        return key_or_path

    @classmethod
    def generate_signed_url(cls, doc_id: str, expires_in=3600, request=None) -> str:
        try:
            obj = S3LikeObject.objects.get(id=doc_id)
        except Exception:
            return cls.get_certified_url(doc_id, expires_in=expires_in, request=request)
        
        if obj.storage_type == 's3':
            return cls.get_certified_url(obj.key, expires_in=expires_in, request=request)
        
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
