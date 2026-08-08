import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from commonUtility.decorators import require_post
from commonUtility.utils import mandatoryInputCheck
from exception import MandatoryInputMissingException
from common.models import User, DomainLookup
from master_management.models import StateMaster, DistrictMaster, BlockMaster, VillageMaster, ContractorMaster, TransformerMaster, ConductorMaster, PoleMaster
from .models import ErectionExecution, ErectionNode

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
        "state_id": 1,
        "district_id": 2,
        "block_id": 3,
        "village_id": 4,
        "contractor_id": 1,
        "type_of_work": 1,
        "lt_starting_point": 1,
        "remarks": "Some remarks"
    }
    """
    logger.warning('================================== START - Erection Execution Start =================================')
    payload = request.data
    
    # Normalize potential spelling typo from FE
    if 'distrct_id' in payload and 'district_id' not in payload:
        payload['district_id'] = payload.get('distrct_id')

    # Validate Mandatory Inputs
    required_fields = ["drawing_no", "state_id", "district_id", "block_id", "village_id", "contractor_id", "type_of_work"]
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
        state_id=payload.get('state_id'),
        district_id=payload.get('district_id'),
        block_id=payload.get('block_id'),
        village_id=payload.get('village_id'),
        contractor_id=payload.get('contractor_id'),
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
    
    # Query mappings to avoid N+1 database queries
    state_map = {s.id: s.state_name for s in StateMaster.objects.all()}
    district_map = {d.id: d.district_name for d in DistrictMaster.objects.all()}
    block_map = {b.id: b.block_name for b in BlockMaster.objects.all()}
    village_map = {v.id: v.village_name for v in VillageMaster.objects.all()}
    contractor_map = {c.id: c.contractor_name for c in ContractorMaster.objects.all()}
    
    domain_map = {}
    for dl in DomainLookup.objects.filter(domain_type__in=['type_of_work', 'lt_starting_point'], status=1):
        domain_map[(dl.domain_type, dl.domain_code)] = {
            "value": dl.domain_value,
            "desc": dl.domain_desc
        }
        
    data_list = []
    for item in erections:
        tow_info = domain_map.get(('type_of_work', item.type_of_work), {})
        ltsp_info = domain_map.get(('lt_starting_point', item.lt_starting_point), {})
        
        data_list.append({
            "id": item.id,
            "feeder_name": item.feeder_name,
            "dtr_code": item.dtr_code,
            "drawing_no": item.drawing_no,
            
            "state_id": item.state_id,
            "state_name": state_map.get(item.state_id),
            
            "district_id": item.district_id,
            "distrct_id": item.district_id,  # Support spelling typo
            "district_name": district_map.get(item.district_id),
            
            "block_id": item.block_id,
            "block_name": block_map.get(item.block_id),
            
            "village_id": item.village_id,
            "village_name": village_map.get(item.village_id),
            
            "contractor_id": item.contractor_id,
            "contractor_name": contractor_map.get(item.contractor_id),
            
            "type_of_work": item.type_of_work,
            "type_of_work_name": tow_info.get('value'),
            "type_of_work_desc": tow_info.get('desc'),
            
            "lt_starting_point": item.lt_starting_point,
            "lt_starting_point_name": ltsp_info.get('value'),
            "lt_starting_point_desc": ltsp_info.get('desc'),
            
            "remarks": item.remarks,
            "status": item.status,
            "created_on": item.created_on.strftime('%Y-%m-%d %H:%M:%S') if item.created_on else None,
            "updated_on": item.updated_on.strftime('%Y-%m-%d %H:%M:%S') if item.updated_on else None,
            "has_nodes": item.nodes.exists(),
            "nodes": [
                {
                    "id": node.id,
                    "nodeType": node.node_type,
                    "sequenceNumber": node.sequence_number,
                    "nameLabel": node.name_label,
                    "latitude": float(node.latitude),
                    "longitude": float(node.longitude),
                    "attributes": node.attributes,
                    "imageUri": node.image_path,
                    "capturedAt": node.captured_at.isoformat() if node.captured_at else None,
                    "parentLabel": node.parent_label,
                }
                for node in item.nodes.all().order_by('sequence_number')
            ]
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
    if 'state_id' in payload:
        erection.state_id = payload.get('state_id')
    if 'district_id' in payload or 'distrct_id' in payload:
        erection.district_id = payload.get('district_id') or payload.get('distrct_id')
    if 'block_id' in payload:
        erection.block_id = payload.get('block_id')
    if 'village_id' in payload:
        erection.village_id = payload.get('village_id')
    if 'contractor_id' in payload:
        erection.contractor_id = payload.get('contractor_id')
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


@csrf_exempt
@require_post
def save_erection_node(request):
    logger.warning('================================== START - Save Erection Node =================================')
    payload = request.data
    
    erection_id = payload.get('erection_execution_id')
    if not erection_id:
        return JsonResponse({"Exception": True, "Message": "Erection Execution ID is required"}, status=400)
        
    erection = ErectionExecution.objects.filter(id=erection_id).first()
    if not erection:
        return JsonResponse({"Exception": True, "Message": "Erection Execution not found"}, status=404)
        
    token_details = getattr(request, 'token_details', None)
    user_id = token_details.get('user_id') if token_details else payload.get('user_id')
    
    from django.utils import timezone
    import datetime
    import json
    
    captured_at_str = payload.get('captured_at')
    if captured_at_str:
        try:
            captured_at = datetime.datetime.fromisoformat(captured_at_str)
        except Exception:
            captured_at = timezone.now()
    else:
        captured_at = timezone.now()
        
    attrs = payload.get('attributes', {})
    node_type = payload.get('node_type')
    
    # Helper to parse integers safely
    def clean_int(val):
        try:
            return int(val) if val is not None and str(val).strip() != '' else None
        except ValueError:
            return None

    # Load ForeignKey relations or set to None
    dtr_capacity_id = clean_int(attrs.get('dtrCapacity'))
    dtr_capacity_obj = TransformerMaster.objects.filter(id=dtr_capacity_id).first() if dtr_capacity_id else None
    
    conductor_id = clean_int(attrs.get('conductor'))
    conductor_obj = ConductorMaster.objects.filter(id=conductor_id).first() if conductor_id else None
    
    pole_type_id = clean_int(attrs.get('poleType'))
    pole_obj = PoleMaster.objects.filter(id=pole_type_id).first() if pole_type_id else None
    
    # Deserialize JSON fields
    pole_db_type_codes = []
    p_types_raw = attrs.get('poleDbTypes')
    if p_types_raw:
        try:
            pole_db_type_codes = json.loads(p_types_raw) if isinstance(p_types_raw, str) else p_types_raw
        except Exception:
            pole_db_type_codes = []
            
    pole_db_quantities = {}
    p_qtys_raw = attrs.get('poleDbQuantities')
    if p_qtys_raw:
        try:
            pole_db_quantities = json.loads(p_qtys_raw) if isinstance(p_qtys_raw, str) else p_qtys_raw
        except Exception:
            pole_db_quantities = {}

    dtr_serial_no = attrs.get('dtrSerialNo') or attrs.get('nameLabel') or payload.get('name_label')
    if node_type == 'DTR':
        dtr_serial_no = payload.get('name_label')
        
    # Query if node exists for this erection at this sequence
    node = ErectionNode.objects.filter(
        erection_execution=erection,
        sequence_number=payload.get('sequence_number')
    ).first()
    
    if node:
        node.node_type = node_type or node.node_type
        node.name_label = payload.get('name_label', node.name_label)
        node.latitude = payload.get('latitude', node.latitude)
        node.longitude = payload.get('longitude', node.longitude)
        node.attributes = attrs
        node.captured_at = captured_at
        node.user_id = user_id
        
        # Explicit fields
        node.dtr_capacity = dtr_capacity_obj
        node.dtr_serial_no = dtr_serial_no
        node.conductor = conductor_obj
        node.structure_condition = attrs.get('assetStatus') or payload.get('assetStatus')
        node.earthing_used = attrs.get('earthingUsed')
        node.earthing_quantity = clean_int(attrs.get('earthingQuantity'))
        node.stay_set_used = attrs.get('staySetUsed')
        node.stay_set_quantity = clean_int(attrs.get('staySetQuantity'))
        node.pole_db_type_codes = pole_db_type_codes
        node.pole_db_quantities = pole_db_quantities
        node.dead_end_clamp_qty = clean_int(attrs.get('deadEndClampQty'))
        node.suspension_clamp_qty = clean_int(attrs.get('suspensionClampQty'))
        node.pole_clamp_qty = clean_int(attrs.get('poleClampQty'))
        node.ipc_qty = clean_int(attrs.get('ipcQty'))
        node.service_connection_qty = clean_int(attrs.get('serviceConnectionQty'))
        node.extra_consumption = clean_int(attrs.get('extraConsumption'))
        node.pole_type = pole_obj
        node.pole_qty = clean_int(attrs.get('poleQty'))
        
        node.save()
        message = "Erection Node updated successfully"
    else:
        node = ErectionNode.objects.create(
            erection_execution=erection,
            node_type=node_type,
            sequence_number=payload.get('sequence_number'),
            name_label=payload.get('name_label'),
            latitude=payload.get('latitude'),
            longitude=payload.get('longitude'),
            attributes=attrs,
            captured_at=captured_at,
            user_id=user_id,
            
            # Explicit fields
            dtr_capacity=dtr_capacity_obj,
            dtr_serial_no=dtr_serial_no,
            conductor=conductor_obj,
            structure_condition=attrs.get('assetStatus') or payload.get('assetStatus'),
            earthing_used=attrs.get('earthingUsed'),
            earthing_quantity=clean_int(attrs.get('earthingQuantity')),
            stay_set_used=attrs.get('staySetUsed'),
            stay_set_quantity=clean_int(attrs.get('staySetQuantity')),
            pole_db_type_codes=pole_db_type_codes,
            pole_db_quantities=pole_db_quantities,
            dead_end_clamp_qty=clean_int(attrs.get('deadEndClampQty')),
            suspension_clamp_qty=clean_int(attrs.get('suspensionClampQty')),
            pole_clamp_qty=clean_int(attrs.get('poleClampQty')),
            ipc_qty=clean_int(attrs.get('ipcQty')),
            service_connection_qty=clean_int(attrs.get('serviceConnectionQty')),
            extra_consumption=clean_int(attrs.get('extraConsumption')),
            pole_type=pole_obj,
            pole_qty=clean_int(attrs.get('poleQty'))
        )
        message = "Erection Node saved successfully"
        
    response_data = {
        "Code": "SUCCESS001",
        "Message": message,
        "Data": {
            "id": node.id,
            "erection_execution_id": erection.id,
            "sequence_number": node.sequence_number,
            "updated_at": node.updated_on.strftime('%Y-%m-%d %H:%M:%S') if node.updated_on else None
        }
    }
    logger.warning('================================== END - Save Erection Node =================================')
    return JsonResponse(response_data)

