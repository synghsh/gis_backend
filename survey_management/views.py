import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from commonUtility.decorators import require_post
from commonUtility.utils import mandatoryInputCheck
from exception import MandatoryInputMissingException
from common.models import User, DomainLookup
from master_management.models import StateMaster, DistrictMaster, BlockMaster, VillageMaster, ContractorMaster, TransformerMaster, ConductorMaster, PoleMaster
from .models import ErectionExecution, ErectionNode, ErectionNodeImage

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
                    "imageUris": [img.image_path for img in node.node_images.all()],
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
    """
    Saves or patches an erection node. Supports both POST and PATCH methods.
    Locates erection by erection_execution_id (numeric or 'erect-X') or drawing_no fallback.
    Locates existing node by node_id, sequence_number, or name_label to update/patch.
    Extracts structure fields from both root payload and attributes dictionary (supporting camelCase & snake_case).
    """
    logger.warning('================================== START - Save Erection Node =================================')
    payload = request.data
    
    # Helper to parse integers safely from ints, floats, or strings
    def clean_int(val):
        if val is None:
            return None
        if isinstance(val, int):
            return val
        s = str(val).strip().replace('erect-', '').replace('srv-', '')
        return int(s) if s.isdigit() else None

    raw_erection_id = payload.get('erection_execution_id') or payload.get('erection_id')
    drawing_no = payload.get('drawing_no') or (payload.get('attributes') or {}).get('drawingNo')
    
    erection = None
    clean_eid = clean_int(raw_erection_id)
    if clean_eid:
        erection = ErectionExecution.objects.filter(id=clean_eid).first()
    if not erection and drawing_no:
        erection = ErectionExecution.objects.filter(drawing_no=str(drawing_no).strip()).order_by('-updated_on').first()
        
    if not erection:
        if not raw_erection_id and not drawing_no:
            return JsonResponse({"Exception": True, "Message": "Either erection_execution_id or drawing_no is required"}, status=400)
        return JsonResponse({"Exception": True, "Message": f"Erection Execution not found for id '{raw_erection_id}' / drawing '{drawing_no}'"}, status=404)
        
    token_details = getattr(request, 'token_details', None)
    user_id = token_details.get('user_id') if token_details else payload.get('user_id')
    
    from django.utils import timezone
    import datetime
    import json
    
    captured_at_str = payload.get('captured_at') or payload.get('capturedAt')
    if captured_at_str:
        try:
            captured_at = datetime.datetime.fromisoformat(captured_at_str)
        except Exception:
            captured_at = timezone.now()
    else:
        captured_at = timezone.now()
        
    attrs = payload.get('attributes') or {}
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except Exception:
            attrs = {}
            
    node_type = payload.get('node_type') or payload.get('nodeType') or attrs.get('nodeType')

    # Load ForeignKey relations or set to None (checking both attrs and root payload)
    dtr_capacity_id = (
        clean_int(attrs.get('dtrCapacity')) or 
        clean_int(attrs.get('dtr_capacity')) or 
        clean_int(attrs.get('transformer')) or 
        clean_int(payload.get('dtrCapacity')) or 
        clean_int(payload.get('dtr_capacity')) or 
        clean_int(payload.get('transformer'))
    )
    dtr_capacity_obj = TransformerMaster.objects.filter(id=dtr_capacity_id).first() if dtr_capacity_id else None
    
    conductor_id = (
        clean_int(attrs.get('conductor')) or 
        clean_int(attrs.get('conductor_type')) or 
        clean_int(payload.get('conductor')) or 
        clean_int(payload.get('conductor_type')) or 
        clean_int(payload.get('conductor_id'))
    )
    conductor_obj = ConductorMaster.objects.filter(id=conductor_id).first() if conductor_id else None
    
    pole_master_id = (
        clean_int(attrs.get('poleMaster')) or 
        clean_int(attrs.get('pole_master')) or 
        clean_int(attrs.get('poleType')) or 
        clean_int(attrs.get('pole_type')) or 
        clean_int(payload.get('poleMaster')) or 
        clean_int(payload.get('pole_master')) or 
        clean_int(payload.get('poleType')) or 
        clean_int(payload.get('pole_type'))
    )
    pole_obj = PoleMaster.objects.filter(id=pole_master_id).first() if pole_master_id else None
    
    # Deserialize JSON fields
    pole_db_type_codes = []
    p_types_raw = attrs.get('poleDbTypes') or attrs.get('pole_db') or payload.get('poleDbTypes') or payload.get('pole_db')
    if p_types_raw:
        try:
            pole_db_type_codes = json.loads(p_types_raw) if isinstance(p_types_raw, str) else p_types_raw
        except Exception:
            pole_db_type_codes = [p_types_raw] if isinstance(p_types_raw, (str, int)) else []
            
    pole_db_quantities = {}
    p_qtys_raw = attrs.get('poleDbQuantities') or attrs.get('pole_db_quantity') or payload.get('poleDbQuantities') or payload.get('pole_db_quantity')
    if p_qtys_raw:
        try:
            pole_db_quantities = json.loads(p_qtys_raw) if isinstance(p_qtys_raw, str) else p_qtys_raw
        except Exception:
            pole_db_quantities = {}

    name_label_val = payload.get('name_label') or payload.get('nameLabel') or attrs.get('nameLabel') or attrs.get('name_label')
    dtr_serial_no = attrs.get('dtrSerialNo') or attrs.get('dtr_serial_no') or name_label_val
    if node_type == 'DTR' and name_label_val:
        dtr_serial_no = name_label_val

    structure_condition = (
        attrs.get('assetStatus') or 
        attrs.get('asset_status') or 
        attrs.get('structureCondition') or 
        attrs.get('structure_condition') or 
        payload.get('assetStatus') or 
        payload.get('asset_status') or 
        payload.get('structure_condition')
    )
    
    earthing_used = attrs.get('earthingUsed') or attrs.get('earthing') or payload.get('earthingUsed') or payload.get('earthing')
    earthing_quantity = clean_int(attrs.get('earthingQuantity') or attrs.get('earthing_quantity') or payload.get('earthingQuantity') or payload.get('earthing_quantity'))
    
    stay_set_used = attrs.get('staySetUsed') or attrs.get('stay_set') or payload.get('staySetUsed') or payload.get('stay_set')
    stay_set_quantity = clean_int(attrs.get('staySetQuantity') or attrs.get('stay_set_quantity') or payload.get('staySetQuantity') or payload.get('stay_set_quantity'))
    
    dead_end_clamp_qty = clean_int(attrs.get('deadEndClampQty') or attrs.get('dead_end_clamp_qty') or attrs.get('dead_end_clamp_quantity') or payload.get('deadEndClampQty'))
    suspension_clamp_qty = clean_int(attrs.get('suspensionClampQty') or attrs.get('suspension_clamp_qty') or attrs.get('suspension_clamp_quantity') or payload.get('suspensionClampQty'))
    pole_clamp_qty = clean_int(attrs.get('poleClampQty') or attrs.get('pole_clamp_qty') or attrs.get('pole_clamp_quantity') or payload.get('poleClampQty'))
    ipc_qty = clean_int(attrs.get('ipcQty') or attrs.get('ipc_qty') or attrs.get('ipc_quantity') or payload.get('ipcQty'))
    service_connection_qty = clean_int(attrs.get('serviceConnectionQty') or attrs.get('service_connection_qty') or attrs.get('service_connection_quantity') or payload.get('serviceConnectionQty'))
    extra_consumption = clean_int(attrs.get('extraConsumption') or attrs.get('extra_consumption') or payload.get('extraConsumption'))
    pole_qty = clean_int(attrs.get('poleQty') or attrs.get('pole_qty') or attrs.get('pole_quantity') or payload.get('poleQty') or payload.get('pole_qty'))
    if pole_qty is None and node_type != 'DTR':
        pole_qty = 1

    latitude = payload.get('latitude') or attrs.get('latitude')
    longitude = payload.get('longitude') or attrs.get('longitude')
    parent_label = payload.get('parent_label') or payload.get('parentLabel') or attrs.get('parentLabel')

    # Query if node exists for this erection:
    # 1. By primary key node_id / id
    node = None
    node_id_val = clean_int(payload.get('node_id') or payload.get('id') or attrs.get('node_id') or attrs.get('id'))
    if node_id_val:
        node = ErectionNode.objects.filter(erection_execution=erection, id=node_id_val).first()
        
    # 2. By sequence_number
    seq_num = clean_int(payload.get('sequence_number') or payload.get('sequenceNumber'))
    if not node and seq_num is not None:
        node = ErectionNode.objects.filter(erection_execution=erection, sequence_number=seq_num).first()
        
    # 3. By name_label
    if not node and name_label_val:
        node = ErectionNode.objects.filter(erection_execution=erection, name_label__iexact=str(name_label_val).strip()).first()
    
    if node:
        # Patch/Update existing node
        node.node_type = node_type or node.node_type
        if name_label_val:
            node.name_label = str(name_label_val).strip()
        if latitude is not None:
            node.latitude = latitude
        if longitude is not None:
            node.longitude = longitude
        if parent_label is not None:
            node.parent_label = parent_label
            
        # Merge existing attributes with new attributes
        merged_attrs = dict(node.attributes or {})
        merged_attrs.update(attrs)
        node.attributes = merged_attrs
        node.captured_at = captured_at
        node.user_id = user_id or node.user_id
        
        # Explicit structure fields
        if dtr_capacity_obj or 'dtrCapacity' in attrs or 'dtr_capacity' in payload:
            node.dtr_capacity = dtr_capacity_obj
        if dtr_serial_no is not None:
            node.dtr_serial_no = dtr_serial_no
        if conductor_obj or 'conductor' in attrs or 'conductor' in payload:
            node.conductor = conductor_obj
        if structure_condition is not None:
            node.structure_condition = structure_condition
        if earthing_used is not None:
            node.earthing_used = earthing_used
        if earthing_quantity is not None:
            node.earthing_quantity = earthing_quantity
        if stay_set_used is not None:
            node.stay_set_used = stay_set_used
        if stay_set_quantity is not None:
            node.stay_set_quantity = stay_set_quantity
        if pole_db_type_codes:
            node.pole_db_type_codes = pole_db_type_codes
        if pole_db_quantities:
            node.pole_db_quantities = pole_db_quantities
        if dead_end_clamp_qty is not None:
            node.dead_end_clamp_qty = dead_end_clamp_qty
        if suspension_clamp_qty is not None:
            node.suspension_clamp_qty = suspension_clamp_qty
        if pole_clamp_qty is not None:
            node.pole_clamp_qty = pole_clamp_qty
        if ipc_qty is not None:
            node.ipc_qty = ipc_qty
        if service_connection_qty is not None:
            node.service_connection_qty = service_connection_qty
        if extra_consumption is not None:
            node.extra_consumption = extra_consumption
        if pole_obj or 'poleMaster' in attrs or 'poleType' in attrs or 'poleType' in payload:
            node.pole_type = pole_obj
        if pole_qty is not None:
            node.pole_qty = pole_qty
        
        node.save()
        message = "Erection Node updated successfully"
    else:
        # Create new node
        target_seq = seq_num if seq_num is not None else (erection.nodes.count() + 1)
        node = ErectionNode.objects.create(
            erection_execution=erection,
            node_type=node_type or 'POLE',
            sequence_number=target_seq,
            name_label=name_label_val or f"P-{target_seq}",
            latitude=latitude or 0.0,
            longitude=longitude or 0.0,
            parent_label=parent_label,
            attributes=attrs,
            captured_at=captured_at,
            user_id=user_id,
            
            # Explicit fields
            dtr_capacity=dtr_capacity_obj,
            dtr_serial_no=dtr_serial_no,
            conductor=conductor_obj,
            structure_condition=structure_condition,
            earthing_used=earthing_used,
            earthing_quantity=earthing_quantity,
            stay_set_used=stay_set_used,
            stay_set_quantity=stay_set_quantity,
            pole_db_type_codes=pole_db_type_codes,
            pole_db_quantities=pole_db_quantities,
            dead_end_clamp_qty=dead_end_clamp_qty,
            suspension_clamp_qty=suspension_clamp_qty,
            pole_clamp_qty=pole_clamp_qty,
            ipc_qty=ipc_qty,
            service_connection_qty=service_connection_qty,
            extra_consumption=extra_consumption,
            pole_type=pole_obj,
            pole_qty=pole_qty
        )
        message = "Erection Node saved successfully"

    # Images saving block
    images_raw = payload.get('images') or attrs.get('images') or payload.get('image_uris') or attrs.get('image_uris') or attrs.get('polePhotos')
    images_list = []
    if images_raw:
        if isinstance(images_raw, str):
            try:
                images_list = json.loads(images_raw)
            except Exception:
                images_list = [img.strip() for img in images_raw.split(',') if img.strip()]
        elif isinstance(images_raw, list):
            images_list = [img for img in images_raw if isinstance(img, str) and img.strip()]

    # Also check other photo categories in attrs if images_list is empty
    if not images_list:
        combined_photos = []
        for cat in ['polePhotos', 'earthingPhotos', 'staySetPhotos', 'poleDbPhotos']:
            p_arr = attrs.get(cat)
            if isinstance(p_arr, list):
                combined_photos.extend([p for p in p_arr if isinstance(p, str) and p.strip()])
        if combined_photos:
            images_list = combined_photos

    if images_list:
        node.image_path = images_list[0]
        node.save()
        ErectionNodeImage.objects.filter(node=node).delete()
        for img_path in images_list:
            if img_path:
                ErectionNodeImage.objects.create(node=node, image_path=img_path)
        
    response_data = {
        "Code": "SUCCESS001",
        "Message": message,
        "Data": {
            "id": node.id,
            "erection_execution_id": erection.id,
            "sequence_number": node.sequence_number,
            "name_label": node.name_label,
            "updated_at": node.updated_on.strftime('%Y-%m-%d %H:%M:%S') if node.updated_on else None
        }
    }
    logger.warning('================================== END - Save Erection Node =================================')
    return JsonResponse(response_data)


@csrf_exempt
@require_post
def get_erection_pole_details(request):
    """
    Fetch pole details for a given drawing number (DWG) / erection and pole identifier.
    Supports both POST and PATCH methods.
    Returns complete data with both camelCase and snake_case properties and structured photo arrays.
    """
    logger.warning('================================== START - Get Erection Pole Details =================================')
    payload = request.data
    
    def clean_int(val):
        if val is None:
            return None
        if isinstance(val, int):
            return val
        s = str(val).strip().replace('erect-', '').replace('srv-', '')
        return int(s) if s.isdigit() else None

    drawing_no = payload.get('drawing_no')
    raw_erection_id = payload.get('erection_id') or payload.get('erection_execution_id')
    pole_no = str(payload.get('pole_no') or payload.get('name_label') or '').strip()
    raw_node_id = payload.get('node_id') or payload.get('id')

    clean_eid = clean_int(raw_erection_id)
    clean_nid = clean_int(raw_node_id)

    if not drawing_no and not clean_eid:
        return JsonResponse({"Exception": True, "Message": "Either drawing_no or erection_id is required"}, status=400)

    erection = None
    if clean_eid:
        erection = ErectionExecution.objects.filter(id=clean_eid).first()
    if not erection and drawing_no:
        erection = ErectionExecution.objects.filter(drawing_no=str(drawing_no).strip()).order_by('-updated_on').first()

    if not erection:
        return JsonResponse({"Exception": True, "Message": f"Erection not found for id '{raw_erection_id}' / drawing '{drawing_no}'"}, status=404)

    nodes_qs = erection.nodes.all().order_by('sequence_number')
    all_poles = [
        {
            "id": n.id,
            "sequenceNumber": n.sequence_number,
            "sequence_number": n.sequence_number,
            "nameLabel": n.name_label,
            "name_label": n.name_label,
            "nodeType": n.node_type,
            "node_type": n.node_type,
            "latitude": float(n.latitude),
            "longitude": float(n.longitude),
            "parentLabel": n.parent_label,
            "parent_label": n.parent_label,
        }
        for n in nodes_qs
    ]

    selected_node = None
    if clean_nid:
        selected_node = nodes_qs.filter(id=clean_nid).first()
    if not selected_node and pole_no:
        selected_node = nodes_qs.filter(name_label__iexact=pole_no).first()
        if not selected_node and pole_no.isdigit():
            selected_node = nodes_qs.filter(sequence_number=int(pole_no)).first()

    node_data = None
    if selected_node:
        all_imgs = [img.image_path for img in selected_node.node_images.all()]
        if not all_imgs and selected_node.image_path:
            all_imgs = [selected_node.image_path]

        attrs = selected_node.attributes or {}
        pole_imgs = attrs.get('polePhotos') or ([selected_node.image_path] if selected_node.image_path else [])
        earthing_imgs = attrs.get('earthingPhotos') or []
        stay_set_imgs = attrs.get('staySetPhotos') or []
        pole_db_imgs = attrs.get('poleDbPhotos') or []

        node_data = {
            "id": selected_node.id,
            "node_id": selected_node.id,
            "erection_execution_id": erection.id,
            "erection_id": erection.id,
            "drawing_no": erection.drawing_no,
            "drawingNo": erection.drawing_no,
            "nodeType": selected_node.node_type,
            "node_type": selected_node.node_type,
            "sequenceNumber": selected_node.sequence_number,
            "sequence_number": selected_node.sequence_number,
            "nameLabel": selected_node.name_label,
            "name_label": selected_node.name_label,
            "latitude": float(selected_node.latitude),
            "longitude": float(selected_node.longitude),
            "parentLabel": selected_node.parent_label,
            "parent_label": selected_node.parent_label,
            "capturedAt": selected_node.captured_at.isoformat() if selected_node.captured_at else None,
            "captured_at": selected_node.captured_at.isoformat() if selected_node.captured_at else None,
            
            # Transformer / DTR
            "dtrCapacity": selected_node.dtr_capacity_id,
            "dtr_capacity": selected_node.dtr_capacity_id,
            "transformer": selected_node.dtr_capacity_id,
            "dtrCapacityName": selected_node.dtr_capacity.transformer_name if selected_node.dtr_capacity else None,
            "dtrSerialNo": selected_node.dtr_serial_no,
            "dtr_serial_no": selected_node.dtr_serial_no,
            
            # Conductor
            "conductor": selected_node.conductor_id,
            "conductor_type": selected_node.conductor_id,
            "conductorName": selected_node.conductor.conductor_name if selected_node.conductor else None,
            
            # Pole
            "poleType": selected_node.pole_type_id,
            "pole_type": selected_node.pole_type_id,
            "poleMaster": selected_node.pole_type_id,
            "pole_master": selected_node.pole_type_id,
            "poleTypeName": selected_node.pole_type.pole_name if selected_node.pole_type else None,
            "poleQty": selected_node.pole_qty,
            "pole_quantity": selected_node.pole_qty,
            
            # Condition / Status
            "assetStatus": selected_node.structure_condition or attrs.get('assetStatus'),
            "asset_status": selected_node.structure_condition or attrs.get('assetStatus'),
            "structureCondition": selected_node.structure_condition,
            "structure_condition": selected_node.structure_condition,
            
            # Earthing
            "earthingUsed": selected_node.earthing_used,
            "earthing": selected_node.earthing_used,
            "earthingQuantity": selected_node.earthing_quantity,
            "earthing_quantity": selected_node.earthing_quantity,
            
            # Stay Set
            "staySetUsed": selected_node.stay_set_used,
            "stay_set": selected_node.stay_set_used,
            "staySetQuantity": selected_node.stay_set_quantity,
            "stay_set_quantity": selected_node.stay_set_quantity,
            
            # Pole DB
            "poleDbTypes": selected_node.pole_db_type_codes or [],
            "pole_db": selected_node.pole_db_type_codes or [],
            "poleDbQuantities": selected_node.pole_db_quantities or {},
            "pole_db_quantity": selected_node.pole_db_quantities or {},
            
            # Clamps & Accessories
            "deadEndClampQty": selected_node.dead_end_clamp_qty,
            "dead_end_clamp_qty": selected_node.dead_end_clamp_qty,
            "dead_end_clamp_quantity": selected_node.dead_end_clamp_qty,
            "suspensionClampQty": selected_node.suspension_clamp_qty,
            "suspension_clamp_qty": selected_node.suspension_clamp_qty,
            "suspension_clamp_quantity": selected_node.suspension_clamp_qty,
            "poleClampQty": selected_node.pole_clamp_qty,
            "pole_clamp_qty": selected_node.pole_clamp_qty,
            "pole_clamp_quantity": selected_node.pole_clamp_qty,
            "ipcQty": selected_node.ipc_qty,
            "ipc_qty": selected_node.ipc_qty,
            "ipc_quantity": selected_node.ipc_qty,
            "serviceConnectionQty": selected_node.service_connection_qty,
            "service_connection_qty": selected_node.service_connection_qty,
            "service_connection_quantity": selected_node.service_connection_qty,
            "extraConsumption": selected_node.extra_consumption,
            "extra_consumption": selected_node.extra_consumption,
            
            # Photos & Attributes
            "attributes": attrs,
            "imageUri": selected_node.image_path,
            "imageUris": all_imgs,
            "images": all_imgs,
            "photo_url": selected_node.image_path,
            "polePhotos": pole_imgs,
            "pole_photo_urls": pole_imgs,
            "earthingPhotos": earthing_imgs,
            "earthing_photo_urls": earthing_imgs,
            "staySetPhotos": stay_set_imgs,
            "stay_set_photo_urls": stay_set_imgs,
            "poleDbPhotos": pole_db_imgs,
            "pole_db_photo_urls": pole_db_imgs,
        }

    response_data = {
        "Code": "SUCCESS001",
        "Message": "Pole details fetched successfully",
        "Data": {
            "drawing_no": erection.drawing_no,
            "drawingNo": erection.drawing_no,
            "erection_id": erection.id,
            "selected_node": node_data,
            "all_poles": all_poles,
        }
    }
    logger.warning('================================== END - Get Erection Pole Details =================================')
    return JsonResponse(response_data)
