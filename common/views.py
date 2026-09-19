import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from exception import MandatoryInputMissingException, BadRequest
from commonUtility.decorators import require_post
from commonUtility.storage import StorageService
from common.models import S3LikeObject

logger = logging.getLogger(__name__)

@csrf_exempt
@require_post
def upload_document(request):
    """
    POST multipart/form-data
    Fields:
      - file: Raw image/file upload
      - bucket (optional): Target bucket
      - prefix (optional): Key folder prefix
      - category (optional): POLE, EARTHING, etc.
      - erection_id (optional): Erection ID
      - pole_label (optional): Pole name
    """
    logger.info("Starting document upload API")
    if 'file' not in request.FILES:
        raise BadRequest("No file found in the request (use field name 'file')")
        
    uploaded_file = request.FILES['file']
    bucket = request.POST.get('bucket') or getattr(request, 'data', {}).get('bucket') or 'gis-image'
    prefix = request.POST.get('prefix') or getattr(request, 'data', {}).get('prefix') or 'GIS/erections'
    erection_id = request.POST.get('erection_id') or getattr(request, 'data', {}).get('erection_id')
    pole_label = request.POST.get('pole_label') or getattr(request, 'data', {}).get('pole_label')
    category = request.POST.get('category') or getattr(request, 'data', {}).get('category')

    if erection_id and pole_label:
        prefix = f"GIS/erections/{erection_id}/{pole_label}"
    elif erection_id:
        prefix = f"GIS/erections/{erection_id}"

    file_data = uploaded_file.read()
    content_type = uploaded_file.content_type or 'image/jpeg'
    file_name = uploaded_file.name
    if category and not file_name.startswith(category):
        file_name = f"{category}_{file_name}"
    
    logger.info(f"[Upload] Uploading {file_name} ({len(file_data)} bytes) to bucket '{bucket}' with prefix '{prefix}'")
    # Upload and compress (if image)
    db_obj = StorageService.upload_file(file_name, file_data, content_type, bucket, prefix=prefix)
    signed_url = StorageService.get_certified_url(db_obj.key)
    logger.info(f"[Upload] Successfully stored in R2: key='{db_obj.key}', size={db_obj.size} bytes")
    
    file_info = {
        "doc_id": str(db_obj.id),
        "bucket": db_obj.bucket,
        "key": db_obj.key,
        "signed_url": signed_url,
        "content_type": db_obj.content_type,
        "size": db_obj.size
    }
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Document uploaded and compressed successfully to Cloudflare R2",
        "data": file_info,
        "Data": file_info
    })

@csrf_exempt
@require_post
def get_signed_url(request):
    """
    POST API to generate a signed URL for a given document.
    Payload:
      {
         "doc_id": "uuid-string",
         "expires_in": 3600 (optional)
      }
    """
    payload = request.data
    doc_id = payload.get('doc_id')
    expires_in = int(payload.get('expires_in', 3600))
    
    if not doc_id:
        raise MandatoryInputMissingException("doc_id is a required field")
        
    try:
        signed_url = StorageService.generate_signed_url(doc_id, expires_in, request)
    except S3LikeObject.DoesNotExist:
        return JsonResponse({"Message": "Document not found"}, status=404)
        
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Signed URL generated successfully",
        "data": {
            "signed_url": signed_url
        }
    })

def download_document(request, doc_id):
    """
    GET request (Token verification bypassed).
    Query Parameters:
      - expires: timestamp
      - signature: hmac signature
    """
    expires = request.GET.get('expires')
    signature = request.GET.get('signature')
    
    if not expires or not signature:
        return HttpResponse("Unauthorized: Missing expires or signature", status=403)
        
    # Verify signature
    is_valid = StorageService.verify_signature(str(doc_id), expires, signature)
    if not is_valid:
        return HttpResponse("Unauthorized: Signature invalid or link expired", status=403)
        
    try:
        file_bytes, content_type = StorageService.get_file_data(str(doc_id))
    except S3LikeObject.DoesNotExist:
        return HttpResponse("Document not found", status=404)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return HttpResponse("Failed to retrieve resource", status=500)
        
    response = HttpResponse(file_bytes, content_type=content_type)
    # Check if user wants inline viewing or download attachment
    if request.GET.get('download') == 'true':
        try:
            obj = S3LikeObject.objects.get(id=doc_id)
            filename = obj.key.split('/')[-1]
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        except Exception:
            pass
    return response
