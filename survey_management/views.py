import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from commonUtility.decorators import require_post
from commonUtility.utils import mandatoryInputCheck
from exception import MandatoryInputMissingException
from common.models import User
from .models import ErectionExecution

logger = logging.getLogger(__name__)

@csrf_exempt
@require_post
def start_erection_execution(request):
    """
    POST Request:
    {
        "feeder_name": "Feeder A",
        "dtr_code": "DTR-123",
        "drawing_no": "DRW-456",
        "state_name": "West Bengal",
        "district": "North 24 Parganas",
        "block": "Barasat I",
        "village": "Chhoto Jagulia",
        "contractor_name": "Bengal Power Works",
        "type_of_work": "HT_11KV",
        "lt_starting_point": "HT_TAPPING_POINT",
        "remarks": "Some remarks"
    }
    """
    logger.warning('================================== START - Erection Execution Start =================================')
    payload = request.data
    
    # Validate Mandatory Inputs
    required_fields = ["drawing_no", "state_id", "district_id", "block_id", "village_id", "contractor_name", "type_of_work"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f'Mandatory Required Fields: {required_fields}')
        
    token_details = getattr(request, 'token_details', None)
    user_id = token_details.get('user_id') if token_details else None
    
    user_obj = None
    if user_id:
        user_obj = User.objects.filter(id=user_id).first()
        
    erection = ErectionExecution.objects.create(
        feeder_name=payload.get('feeder_name'),
        dtr_code=payload.get('dtr_code'),
        drawing_no=payload.get('drawing_no'),
        state_name=payload.get('state_name'),
        district=payload.get('district'),
        block=payload.get('block'),
        village=payload.get('village'),
        state_id=payload.get('state_id'),
        district_id=payload.get('district_id'),
        block_id=payload.get('block_id'),
        village_id=payload.get('village_id'),
        contractor_name=payload.get('contractor_name'),
        type_of_work=payload.get('type_of_work'),
        lt_starting_point=payload.get('lt_starting_point'),
        remarks=payload.get('remarks'),
        surveyor=user_obj
    )
    
    response_data = {
        "Code": "SUCCESS001",
        "Message": "Erection Execution Started Successfully",
        "ErectionId": erection.id
    }
    
    logger.warning('================================== END - Erection Execution Start =================================')
    return JsonResponse(response_data)


@csrf_exempt
@require_post
def list_erection_executions(request):
    logger.warning('================================== START - Erection Execution List =================================')
    token_details = getattr(request, 'token_details', None)
    user_id = token_details.get('user_id') if token_details else None
    
    if not user_id:
        return JsonResponse({"Exception": True, "Message": "Unauthorized access"}, status=401)
        
    erections = ErectionExecution.objects.filter(surveyor_id=user_id).order_by('-updated_on')
    
    data_list = []
    for item in erections:
        data_list.append({
            "id": item.id,
            "feeder_name": item.feeder_name,
            "dtr_code": item.dtr_code,
            "drawing_no": item.drawing_no,
            "state_name": item.state_name,
            "district": item.district,
            "block": item.block,
            "village": item.village,
            "state_id": item.state_id,
            "district_id": item.district_id,
            "block_id": item.block_id,
            "village_id": item.village_id,
            "contractor_name": item.contractor_name,
            "type_of_work": item.type_of_work,
            "lt_starting_point": item.lt_starting_point,
            "remarks": item.remarks,
            "status": item.status,
            "updated_on": item.updated_on.strftime('%Y-%m-%d %H:%M:%S') if item.updated_on else None
        })
        
    response_data = {
        "Code": "SUCCESS001",
        "Message": "Erection Executions Fetched Successfully",
        "Data": data_list
    }
    logger.warning('================================== END - Erection Execution List =================================')
    return JsonResponse(response_data)


@csrf_exempt
@require_post
def update_erection_execution(request):
    logger.warning('================================== START - Erection Execution Update =================================')
    payload = request.data
    
    erection_id = payload.get('id')
    if not erection_id:
        return JsonResponse({"Exception": True, "Message": "Erection ID is required"}, status=400)
        
    erection = ErectionExecution.objects.filter(id=erection_id).first()
    if not erection:
        return JsonResponse({"Exception": True, "Message": "Erection record not found"}, status=404)
        
    # Update fields
    if 'feeder_name' in payload:
        erection.feeder_name = payload.get('feeder_name')
    if 'dtr_code' in payload:
        erection.dtr_code = payload.get('dtr_code')
    if 'drawing_no' in payload:
        erection.drawing_no = payload.get('drawing_no')
    if 'state_name' in payload:
        erection.state_name = payload.get('state_name')
    if 'district' in payload:
        erection.district = payload.get('district')
    if 'block' in payload:
        erection.block = payload.get('block')
    if 'village' in payload:
        erection.village = payload.get('village')
    if 'state_id' in payload:
        erection.state_id = payload.get('state_id')
    if 'district_id' in payload:
        erection.district_id = payload.get('district_id')
    if 'block_id' in payload:
        erection.block_id = payload.get('block_id')
    if 'village_id' in payload:
        erection.village_id = payload.get('village_id')
    if 'contractor_name' in payload:
        erection.contractor_name = payload.get('contractor_name')
    if 'type_of_work' in payload:
        erection.type_of_work = payload.get('type_of_work')
    if 'lt_starting_point' in payload:
        erection.lt_starting_point = payload.get('lt_starting_point')
    if 'remarks' in payload:
        erection.remarks = payload.get('remarks')
    if 'status' in payload:
        erection.status = payload.get('status')
        
    erection.save()
    
    response_data = {
        "Code": "SUCCESS001",
        "Message": "Erection Execution Updated Successfully",
        "Data": {
            "id": erection.id,
            "status": erection.status
        }
    }
    logger.warning('================================== END - Erection Execution Update =================================')
    return JsonResponse(response_data)


@csrf_exempt
@require_post
def complete_erection_execution(request):
    logger.warning('================================== START - Erection Execution Complete =================================')
    payload = request.data
    
    erection_id = payload.get('id')
    if not erection_id:
        return JsonResponse({"Exception": True, "Message": "Erection ID is required"}, status=400)
        
    erection = ErectionExecution.objects.filter(id=erection_id).first()
    if not erection:
        return JsonResponse({"Exception": True, "Message": "Erection record not found"}, status=404)
        
    erection.status = 2  # Completed
    erection.save()
    
    response_data = {
        "Code": "SUCCESS001",
        "Message": "Erection Execution Completed Successfully",
        "Data": {
            "id": erection.id,
            "status": erection.status
        }
    }
    logger.warning('================================== END - Erection Execution Complete =================================')
    return JsonResponse(response_data)
