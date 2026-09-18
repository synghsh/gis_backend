import logging
import math
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from commonUtility.decorators import require_post
from commonUtility.utils import mandatoryInputCheck
from exception import MandatoryInputMissingException
from common.models import User, DomainLookup
from master_management.models import StateMaster, DistrictMaster, BlockMaster, VillageMaster, ContractorMaster, TransformerMaster, ConductorMaster, PoleMaster
from .models import ErectionExecution, ErectionNode, ErectionNodeImage, SurveyLine, SurveyNode

logger = logging.getLogger(__name__)

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points in meters using Haversine formula."""
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        if (lat1 == 0 and lon1 == 0) or (lat2 == 0 and lon2 == 0):
            return 0.0
        if lat1 == lat2 and lon1 == lon2:
            return 0.0
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return round(R * c, 2)
    except Exception:
        return 0.0

def extract_node_images(node):
    """Consolidate photos from image_path, related images, and attributes dictionary."""
    imgs = []
    if getattr(node, 'image_path', None) and node.image_path not in imgs:
        imgs.append(node.image_path)
    if hasattr(node, 'node_images'):
        for img_obj in node.node_images.all():
            if img_obj.image_path and img_obj.image_path not in imgs:
                imgs.append(img_obj.image_path)
    attrs = getattr(node, 'attributes', None) or {}
    for key in ['polePhotos', 'poleDbPhotos', 'staySetPhotos', 'earthingPhotos', 'photos', 'imageUrls']:
        val = attrs.get(key)
        if isinstance(val, list):
            for p in val:
                if p and p not in imgs:
                    imgs.append(p)
        elif isinstance(val, str) and val and val not in imgs:
            imgs.append(val)
    return imgs

def check_is_new_pole(node):
    """Return True if node represents a NEW pole or structure, False if OLD/EXISTING."""
    attrs = getattr(node, 'attributes', None) or {}
    cond = str(getattr(node, 'structure_condition', None) or attrs.get('assetStatus') or '').upper().strip()
    if cond in ['OLD', 'EXISTING']:
        return False
    if cond == 'NEW':
        return True
    if attrs.get('isNewPole') is False or attrs.get('is_new') is False:
        return False
    return True

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
    user_type = token_details.get('user_type') if token_details else None
    payload = getattr(request, 'data', {}) or {}
    
    # Query mappings to avoid N+1 database queries
    state_map = {s.id: s.state_name for s in StateMaster.objects.all()}
    district_map = {d.id: d.district_name for d in DistrictMaster.objects.all()}
    block_map = {b.id: b.block_name for b in BlockMaster.objects.all()}
    village_map = {v.id: v.village_name for v in VillageMaster.objects.all()}
    contractor_map = {c.id: c.contractor_name for c in ContractorMaster.objects.all()}
    surveyor_map = {u.id: (u.username or u.email) for u in User.objects.all()}
    surveyor_phone_map = {u.id: u.phone for u in User.objects.all()}
    
    domain_map = {}
    for dl in DomainLookup.objects.filter(domain_type__in=['type_of_work', 'lt_starting_point'], status=1):
        domain_map[(dl.domain_type, dl.domain_code)] = {
            "value": dl.domain_value,
            "desc": dl.domain_desc
        }

    # Base QuerySet
    erections = ErectionExecution.objects.all().order_by('-updated_on')

    # Surveyor filtering: if explicit surveyor_id passed, filter by it
    explicit_surveyor = payload.get('surveyor_id')
    if explicit_surveyor:
        erections = erections.filter(surveyor_id=explicit_surveyor)
    elif payload.get('only_my_records'):
        if user_id:
            erections = erections.filter(surveyor_id=user_id)
    elif not payload.get('all') and not payload.get('is_admin'):
        # For non-admin surveyors calling without admin flag, filter to own records if user_id exists
        if user_type != 1 and user_id:
            erections = erections.filter(surveyor_id=user_id)

    # Search filter
    search = payload.get('search')
    if search:
        search = str(search).strip()
        erections = erections.filter(
            Q(drawing_no__icontains=search) |
            Q(feeder_name__icontains=search) |
            Q(dtr_code__icontains=search) |
            Q(remarks__icontains=search)
        )

    # 1. State filter
    state_id = payload.get('state_id') or payload.get('state')
    if state_id is not None and str(state_id).strip() != '' and str(state_id).lower() != 'all':
        try:
            erections = erections.filter(state_id=int(state_id))
        except (ValueError, TypeError):
            pass

    # 2. District filter (handle potential distrct typo as well)
    district_id = payload.get('district_id') or payload.get('distrct_id') or payload.get('district')
    if district_id is not None and str(district_id).strip() != '' and str(district_id).lower() != 'all':
        try:
            erections = erections.filter(district_id=int(district_id))
        except (ValueError, TypeError):
            pass

    # 3. Block filter
    block_id = payload.get('block_id') or payload.get('block')
    if block_id is not None and str(block_id).strip() != '' and str(block_id).lower() != 'all':
        try:
            erections = erections.filter(block_id=int(block_id))
        except (ValueError, TypeError):
            pass

    # 4. Feeder filter
    feeder = payload.get('feeder') or payload.get('feeder_name')
    if feeder is not None and str(feeder).strip() != '' and str(feeder).lower() != 'all':
        erections = erections.filter(feeder_name__icontains=str(feeder).strip())

    # 5. Contractor filter (by ID or contractor name)
    contractor = payload.get('contractor_name') or payload.get('contractor_id') or payload.get('contractor')
    if contractor is not None and str(contractor).strip() != '' and str(contractor).lower() != 'all':
        contractor_str = str(contractor).strip()
        if contractor_str.isdigit():
            erections = erections.filter(contractor_id=int(contractor_str))
        else:
            matching_c_ids = list(ContractorMaster.objects.filter(contractor_name__icontains=contractor_str).values_list('id', flat=True))
            erections = erections.filter(contractor_id__in=matching_c_ids)

    # 6. Line type filter (type of work)
    line_type = payload.get('line_type') or payload.get('type_of_work')
    if line_type is not None and str(line_type).strip() != '' and str(line_type).lower() != 'all':
        line_type_str = str(line_type).strip()
        if line_type_str.isdigit():
            erections = erections.filter(type_of_work=int(line_type_str))
        else:
            matching_codes = list(DomainLookup.objects.filter(
                domain_type='type_of_work',
                status=1
            ).filter(
                Q(domain_value__icontains=line_type_str) |
                Q(domain_desc__icontains=line_type_str)
            ).values_list('domain_code', flat=True))
            if matching_codes:
                erections = erections.filter(type_of_work__in=matching_codes)
            elif '11' in line_type_str:
                erections = erections.filter(type_of_work=1)
            elif 'LT' in line_type_str.upper() or '440' in line_type_str:
                erections = erections.filter(type_of_work=2)
            elif '33' in line_type_str:
                erections = erections.filter(type_of_work=3)

    # 7. Status filter
    status = payload.get('status')
    if status is not None and str(status).strip() != '' and str(status).lower() != 'all':
        try:
            status_int = int(status)
            erections = erections.filter(status=status_int)
        except (ValueError, TypeError):
            pass

    # 8. Start Date and End Date filters (on created_on)
    start_date = payload.get('start_date') or payload.get('from_date')
    if start_date and str(start_date).strip() != '':
        try:
            from datetime import datetime
            start_d = datetime.strptime(str(start_date)[:10], '%Y-%m-%d').date()
            erections = erections.filter(created_on__date__gte=start_d)
        except Exception as e:
            logger.warning(f"Error parsing start_date {start_date}: {e}")

    end_date = payload.get('end_date') or payload.get('to_date')
    if end_date and str(end_date).strip() != '':
        try:
            from datetime import datetime
            end_d = datetime.strptime(str(end_date)[:10], '%Y-%m-%d').date()
            erections = erections.filter(created_on__date__lte=end_d)
        except Exception as e:
            logger.warning(f"Error parsing end_date {end_date}: {e}")

    total_count = erections.count()

    # 9 & 10. Page size and Page index (mandatory for pagination --- if null send all data)
    raw_page_size = payload.get('page_size')
    if raw_page_size is None:
        raw_page_size = payload.get('pageSize')

    raw_page_index = payload.get('page_index')
    if raw_page_index is None:
        raw_page_index = payload.get('pageIndex')
    if raw_page_index is None:
        raw_page_index = payload.get('page_no')

    # Check if either page_size or page_index is omitted or null -> return all data
    is_all_data = False
    if raw_page_size in [None, '', 'null', 'None', 'all', 'ALL'] or raw_page_index in [None, '', 'null', 'None', 'all', 'ALL']:
        is_all_data = True
        page_size = None
        page_index = 1
    else:
        try:
            page_size = int(raw_page_size)
            page_index = int(raw_page_index)
            if page_size <= 0:
                is_all_data = True
                page_size = None
                page_index = 1
            elif page_index < 1:
                page_index = 1
        except (ValueError, TypeError):
            is_all_data = True
            page_size = None
            page_index = 1

    if is_all_data or page_size is None:
        paginated_erections = erections
        total_pages = 1
        current_page = 1
        returned_page_size = total_count
    else:
        offset = (page_index - 1) * page_size
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
        paginated_erections = erections[offset:offset + page_size]
        current_page = page_index
        returned_page_size = page_size
        
    data_list = []
    for item in paginated_erections:
        tow_info = domain_map.get(('type_of_work', item.type_of_work), {})
        ltsp_info = domain_map.get(('lt_starting_point', item.lt_starting_point), {})
        nodes_qs = item.nodes.all().order_by('sequence_number')
        
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
            
            "surveyor_id": item.surveyor_id,
            "surveyor_name": surveyor_map.get(item.surveyor_id, "Unassigned"),
            "surveyor_phone": surveyor_phone_map.get(item.surveyor_id, ""),
            
            "type_of_work": item.type_of_work,
            "type_of_work_name": tow_info.get('value'),
            "type_of_work_desc": tow_info.get('desc'),
            
            "lt_starting_point": item.lt_starting_point,
            "lt_starting_point_name": ltsp_info.get('value'),
            "lt_starting_point_desc": ltsp_info.get('desc'),
            
            "remarks": item.remarks,
            "status": item.status,
            "status_label": "Completed" if item.status == 2 else "Active",
            "created_on": item.created_on.strftime('%Y-%m-%d %H:%M:%S') if item.created_on else None,
            "updated_on": item.updated_on.strftime('%Y-%m-%d %H:%M:%S') if item.updated_on else None,
            "has_nodes": nodes_qs.exists(),
            "nodes_count": nodes_qs.count(),
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
                for node in nodes_qs
            ]
        })
        
    response_data = {
        "Code": "SUCCESS001",
        "Message": "Erection Executions Fetched Successfully",
        "Data": data_list,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": current_page,
        "page_index": current_page,
        "page_size": returned_page_size
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
    
    # Helpers to parse fields safely from payload and attributes
    def clean_int(val):
        if val is None or val == '':
            return None
        if isinstance(val, int):
            return val
        s = str(val).strip().replace('erect-', '').replace('srv-', '')
        return int(s) if s.isdigit() else None

    def get_field_val(sources, *keys, default=None):
        for src in sources:
            if not isinstance(src, dict):
                continue
            for k in keys:
                if k in src and src[k] is not None and src[k] != '':
                    return src[k]
        return default

    def get_int_field_val(sources, *keys, default=None):
        for src in sources:
            if not isinstance(src, dict):
                continue
            for k in keys:
                if k in src and src[k] is not None and src[k] != '':
                    val = clean_int(src[k])
                    if val is not None:
                        return val
        return default

    raw_erection_id = get_field_val([payload], 'erection_execution_id', 'erection_id')
    drawing_no = get_field_val([payload, payload.get('attributes') or {}], 'drawing_no', 'drawingNo')
    
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
    
    captured_at_str = get_field_val([payload], 'captured_at', 'capturedAt')
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
            
    node_type = get_field_val([payload, attrs], 'node_type', 'nodeType')

    # Load ForeignKey relations or set to None (checking both attrs and root payload)
    dtr_capacity_id = get_int_field_val(
        [payload, attrs],
        'dtr_capacity_id', 'dtrCapacityId',
        'dtr_capacity', 'dtrCapacity',
        'transformer', 'transformer_id'
    )
    dtr_capacity_obj = TransformerMaster.objects.filter(id=dtr_capacity_id).first() if dtr_capacity_id else None
    
    conductor_id = get_int_field_val(
        [payload, attrs],
        'conductor_id', 'conductorId',
        'conductor', 'conductor_type', 'conductorType'
    )
    conductor_obj = ConductorMaster.objects.filter(id=conductor_id).first() if conductor_id else None
    
    pole_master_id = get_int_field_val(
        [payload, attrs],
        'pole_type_id', 'poleTypeId',
        'pole_master_id', 'poleMasterId',
        'pole_master', 'poleMaster',
        'pole_type', 'poleType'
    )
    pole_obj = PoleMaster.objects.filter(id=pole_master_id).first() if pole_master_id else None
    
    # Deserialize JSON fields
    pole_db_type_codes = []
    p_types_raw = get_field_val([payload, attrs], 'poleDbTypes', 'pole_db')
    if p_types_raw:
        try:
            pole_db_type_codes = json.loads(p_types_raw) if isinstance(p_types_raw, str) else p_types_raw
        except Exception:
            pole_db_type_codes = [p_types_raw] if isinstance(p_types_raw, (str, int)) else []
            
    pole_db_quantities = {}
    p_qtys_raw = get_field_val([payload, attrs], 'poleDbQuantities', 'pole_db_quantity')
    if p_qtys_raw:
        try:
            pole_db_quantities = json.loads(p_qtys_raw) if isinstance(p_qtys_raw, str) else p_qtys_raw
        except Exception:
            pole_db_quantities = {}

    name_label_val = get_field_val([payload, attrs], 'name_label', 'nameLabel')
    dtr_serial_no = get_field_val([attrs, payload], 'dtrSerialNo', 'dtr_serial_no') or name_label_val
    if node_type == 'DTR' and name_label_val:
        dtr_serial_no = name_label_val

    structure_condition = get_field_val(
        [payload, attrs],
        'structure_condition', 'structureCondition',
        'asset_status', 'assetStatus'
    )
    
    earthing_used = get_field_val([payload, attrs], 'earthing_used', 'earthingUsed', 'earthing')
    earthing_quantity = get_int_field_val([payload, attrs], 'earthing_quantity', 'earthingQuantity')
    
    stay_set_used = get_field_val([payload, attrs], 'stay_set_used', 'staySetUsed', 'stay_set')
    stay_set_quantity = get_int_field_val([payload, attrs], 'stay_set_quantity', 'staySetQuantity')
    
    dead_end_clamp_qty = get_int_field_val([payload, attrs], 'dead_end_clamp_qty', 'deadEndClampQty', 'dead_end_clamp_quantity')
    suspension_clamp_qty = get_int_field_val([payload, attrs], 'suspension_clamp_qty', 'suspensionClampQty', 'suspension_clamp_quantity')
    pole_clamp_qty = get_int_field_val([payload, attrs], 'pole_clamp_qty', 'poleClampQty', 'pole_clamp_quantity')
    ipc_qty = get_int_field_val([payload, attrs], 'ipc_qty', 'ipcQty', 'ipc_quantity')
    service_connection_qty = get_int_field_val([payload, attrs], 'service_connection_qty', 'serviceConnectionQty', 'service_connection_quantity', 'serviceConnectionQuantity', 'service_connection', 'serviceConnection')
    extra_consumption = get_int_field_val([payload, attrs], 'extra_consumption', 'extraConsumption')
    pole_qty = get_int_field_val([payload, attrs], 'pole_qty', 'poleQty', 'pole_quantity')
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
        elif any(k in payload for k in ['service_connection_qty', 'serviceConnectionQty', 'service_connection_quantity']) or \
             any(k in attrs for k in ['service_connection_qty', 'serviceConnectionQty', 'service_connection_quantity']):
            node.service_connection_qty = None

        if extra_consumption is not None:
            node.extra_consumption = extra_consumption
        if pole_obj is not None:
            node.pole_type = pole_obj
        elif any((k in payload and payload[k] in (None, '', 0)) or (k in attrs and attrs[k] in (None, '', 0)) for k in ['pole_type_id', 'poleTypeId', 'pole_master_id', 'poleMasterId', 'pole_master', 'poleMaster']):
            node.pole_type = None
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
            "pole_type_id": node.pole_type_id,
            "service_connection_qty": node.service_connection_qty,
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

    erection = None
    if clean_nid:
        node_direct = ErectionNode.objects.filter(id=clean_nid).first()
        if node_direct:
            erection = node_direct.erection_execution
    if not erection and clean_eid:
        erection = ErectionExecution.objects.filter(id=clean_eid).first()
    if not erection and drawing_no:
        clean_drawing = str(drawing_no).strip()
        erection = ErectionExecution.objects.filter(drawing_no__iexact=clean_drawing).order_by('-updated_on').first()

    if not erection:
        logger.warning(f"Erection not found on server for id '{raw_erection_id}' / drawing '{drawing_no}' / node '{raw_node_id}'. Returning graceful fallback.")
        return JsonResponse({
            "Code": "SUCCESS001",
            "Message": "Node details not found on server, fallback to local cache",
            "Data": {
                "drawing_no": drawing_no,
                "drawingNo": drawing_no,
                "erection_id": clean_eid,
                "selected_node": None,
                "all_poles": [],
            }
        }, status=200)

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
        clean_pno = str(pole_no).strip()
        selected_node = nodes_qs.filter(name_label__iexact=clean_pno).first()
        if not selected_node and clean_pno.isdigit():
            selected_node = nodes_qs.filter(sequence_number=int(clean_pno)).first()
        if not selected_node:
            prefix_match = clean_pno.replace('P-', '').replace('P', '').strip()
            if prefix_match.isdigit():
                selected_node = nodes_qs.filter(sequence_number=int(prefix_match)).first()

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
            "pole_type_id": selected_node.pole_type_id,
            "pole_master_id": selected_node.pole_type_id,
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
        "Message": "Pole details fetched successfully" if node_data else "Pole not found on server, fallback to local cache",
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


@csrf_exempt
@require_post
def get_erection_detail(request):
    logger.warning('================================== START - Get Erection Detail =================================')
    payload = getattr(request, 'data', {}) or {}
    erection_id = payload.get('id') or payload.get('erection_id')
    if not erection_id:
        return JsonResponse({"Exception": True, "Message": "Erection ID is required"}, status=400)
        
    erection = ErectionExecution.objects.filter(id=erection_id).first()
    if not erection:
        return JsonResponse({"Exception": True, "Message": "Erection record not found"}, status=404)
        
    state_map = {s.id: s.state_name for s in StateMaster.objects.all()}
    district_map = {d.id: d.district_name for d in DistrictMaster.objects.all()}
    block_map = {b.id: b.block_name for b in BlockMaster.objects.all()}
    village_map = {v.id: v.village_name for v in VillageMaster.objects.all()}
    contractor_map = {c.id: c.contractor_name for c in ContractorMaster.objects.all()}
    surveyor_map = {u.id: (u.username or u.email) for u in User.objects.all()}
    surveyor_phone_map = {u.id: u.phone for u in User.objects.all()}
    surveyor_email_map = {u.id: u.email for u in User.objects.all()}

    domain_map = {}
    for dl in DomainLookup.objects.filter(domain_type__in=['type_of_work', 'lt_starting_point'], status=1):
        domain_map[(dl.domain_type, dl.domain_code)] = {
            "value": dl.domain_value,
            "desc": dl.domain_desc
        }

    tow_info = domain_map.get(('type_of_work', erection.type_of_work), {})
    ltsp_info = domain_map.get(('lt_starting_point', erection.lt_starting_point), {})

    def parse_qty(val):
        if val is None:
            return 0
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return 0

    nodes_data = []
    prev_node = None
    total_route_distance = 0.0
    day_groups = {}
    conductor_names_set = set()
    pole_db_summary = {}

    for node in erection.nodes.all().order_by('sequence_number'):
        node_imgs = extract_node_images(node)
        is_new = check_is_new_pole(node)
        
        # Distance calculation
        if prev_node:
            dist_to_prev = calculate_haversine_distance(
                prev_node.latitude, prev_node.longitude,
                node.latitude, node.longitude
            )
        else:
            dist_to_prev = 0.0
            
        total_route_distance += dist_to_prev
        prev_node = node
        
        # Conductor resolving
        c_name = node.conductor.conductor_name if node.conductor else (node.attributes or {}).get('cableSize')
        if c_name:
            conductor_names_set.add(str(c_name))

        attrs = node.attributes or {}
        earthing_qty = parse_qty(node.earthing_quantity if node.earthing_quantity is not None else attrs.get('earthingQuantity'))
        stay_set_qty = parse_qty(node.stay_set_quantity if node.stay_set_quantity is not None else attrs.get('staySetQuantity'))
        dead_end_qty = parse_qty(node.dead_end_clamp_qty if node.dead_end_clamp_qty is not None else attrs.get('deadEndClampQty'))
        suspension_qty = parse_qty(node.suspension_clamp_qty if node.suspension_clamp_qty is not None else attrs.get('suspensionClampQty'))
        pole_clamp_qty = parse_qty(node.pole_clamp_qty if node.pole_clamp_qty is not None else attrs.get('poleClampQty'))
        ipc_qty = parse_qty(node.ipc_qty if node.ipc_qty is not None else attrs.get('ipcQty'))
        service_conn_qty = parse_qty(node.service_connection_qty if node.service_connection_qty is not None else attrs.get('serviceConnectionQty'))
        extra_consump = parse_qty(node.extra_consumption if node.extra_consumption is not None else attrs.get('extraConsumption'))
        pole_qty = parse_qty(node.pole_qty if node.pole_qty is not None else attrs.get('poleQty', 1 if node.node_type == 'POLE' else 0))

        # Pole DB quantities
        db_quantities = node.pole_db_quantities or {}
        if not db_quantities and 'poleDbQuantities' in attrs:
            import json
            raw_db = attrs.get('poleDbQuantities')
            if isinstance(raw_db, str):
                try: db_quantities = json.loads(raw_db)
                except Exception: db_quantities = {}
            elif isinstance(raw_db, dict):
                db_quantities = raw_db

        if isinstance(db_quantities, dict):
            for db_type, q in db_quantities.items():
                parsed_q = parse_qty(q)
                pole_db_summary[str(db_type)] = pole_db_summary.get(str(db_type), 0) + parsed_q

        node_dict = {
            "id": node.id,
            "node_type": node.node_type,
            "sequence_number": node.sequence_number,
            "name_label": node.name_label,
            "latitude": float(node.latitude),
            "longitude": float(node.longitude),
            "distance_to_prev_meters": dist_to_prev,
            "cumulative_distance_meters": round(total_route_distance, 2),
            "is_new_pole": is_new,
            "structure_condition": "NEW" if is_new else "OLD",
            "structure_condition_label": "New Pole" if (node.node_type == 'POLE' and is_new) else ("Old Pole" if node.node_type == 'POLE' else "DTR"),
            "dtr_capacity_id": node.dtr_capacity_id,
            "dtr_capacity_name": node.dtr_capacity.transformer_name if node.dtr_capacity else attrs.get('dtrCapacity'),
            "dtr_serial_no": node.dtr_serial_no or attrs.get('dtrSerialNo'),
            "conductor_id": node.conductor_id,
            "conductor_name": c_name,
            "earthing_used": node.earthing_used or str(attrs.get('earthingUsed', '')),
            "earthing_quantity": earthing_qty,
            "stay_set_used": node.stay_set_used or str(attrs.get('staySetUsed', '')),
            "stay_set_quantity": stay_set_qty,
            "pole_type_id": node.pole_type_id,
            "pole_type_name": node.pole_type.pole_name if node.pole_type else attrs.get('poleType'),
            "pole_qty": pole_qty,
            "dead_end_clamp_qty": dead_end_qty,
            "suspension_clamp_qty": suspension_qty,
            "pole_clamp_qty": pole_clamp_qty,
            "ipc_qty": ipc_qty,
            "service_connection_qty": service_conn_qty,
            "extra_consumption": extra_consump,
            "pole_db_type_codes": node.pole_db_type_codes or attrs.get('poleDbTypes'),
            "pole_db_quantities": db_quantities,
            "attributes": attrs,
            "image_path": node.image_path,
            "images": node_imgs,
            "parent_label": node.parent_label,
            "captured_at": node.captured_at.strftime('%Y-%m-%d %H:%M:%S') if node.captured_at else None,
        }
        nodes_data.append(node_dict)

        # Day-wise grouping based on captured_at or created_on
        node_dt = node.captured_at or node.created_on
        date_key = node_dt.strftime('%Y-%m-%d') if node_dt else 'Initial Entry'
        if date_key not in day_groups:
            day_groups[date_key] = {
                "date": date_key,
                "raw_date": node_dt.date() if node_dt else None,
                "nodes": [],
                "poles_erected": 0,
                "new_poles": 0,
                "old_poles": 0,
                "dtrs_erected": 0,
                "span_meters": 0.0,
                "photos_count": 0,
                "materials": {
                    "earthing": 0,
                    "stay_set": 0,
                    "dead_end_clamp": 0,
                    "suspension_clamp": 0,
                    "pole_clamp": 0,
                    "ipc": 0,
                    "service_connection": 0,
                    "extra_consumption": 0,
                    "pole_qty": 0,
                    "pole_db": 0
                }
            }
        
        dg = day_groups[date_key]
        dg["nodes"].append(node_dict)
        if node.node_type == 'POLE':
            dg["poles_erected"] += 1
            if is_new:
                dg["new_poles"] += 1
            else:
                dg["old_poles"] += 1
        elif node.node_type == 'DTR':
            dg["dtrs_erected"] += 1

        dg["span_meters"] += dist_to_prev
        dg["photos_count"] += len(node_imgs)
        dg["materials"]["earthing"] += earthing_qty
        dg["materials"]["stay_set"] += stay_set_qty
        dg["materials"]["dead_end_clamp"] += dead_end_qty
        dg["materials"]["suspension_clamp"] += suspension_qty
        dg["materials"]["pole_clamp"] += pole_clamp_qty
        dg["materials"]["ipc"] += ipc_qty
        dg["materials"]["service_connection"] += service_conn_qty
        dg["materials"]["extra_consumption"] += extra_consump
        dg["materials"]["pole_qty"] += pole_qty
        if isinstance(db_quantities, dict):
            for _, q in db_quantities.items():
                dg["materials"]["pole_db"] += parse_qty(q)

    # Format Day-Wise Progress
    sorted_days = sorted(day_groups.values(), key=lambda x: x["date"])
    day_progress_list = []
    for idx, day in enumerate(sorted_days, 1):
        summary_parts = []
        if day["dtrs_erected"] > 0:
            summary_parts.append(f"{day['dtrs_erected']} DTR installed")
        if day["new_poles"] > 0:
            summary_parts.append(f"{day['new_poles']} New Pole(s) erected")
        if day["old_poles"] > 0:
            summary_parts.append(f"{day['old_poles']} Old Pole(s) connected/worked on")
        
        m = day["materials"]
        mat_parts = []
        if m["earthing"] > 0: mat_parts.append(f"{m['earthing']} Earthing")
        if m["stay_set"] > 0: mat_parts.append(f"{m['stay_set']} Stay Set(s)")
        if m["ipc"] > 0: mat_parts.append(f"{m['ipc']} IPC(s)")
        if m["dead_end_clamp"] > 0: mat_parts.append(f"{m['dead_end_clamp']} Dead-end clamp(s)")
        if m["suspension_clamp"] > 0: mat_parts.append(f"{m['suspension_clamp']} Suspension clamp(s)")
        if m["service_connection"] > 0: mat_parts.append(f"{m['service_connection']} Service conn(s)")
        if m["pole_db"] > 0: mat_parts.append(f"{m['pole_db']} Pole DB(s)")

        day_progress_list.append({
            "day_number": idx,
            "date": day["date"],
            "nodes_count": len(day["nodes"]),
            "nodes_summary": [f"{n['name_label']} ({n['structure_condition_label']})" for n in day["nodes"]],
            "work_description": ", ".join(summary_parts) if summary_parts else "Materials entry and verification",
            "materials_summary": ", ".join(mat_parts) if mat_parts else "No additional materials recorded",
            "materials": day["materials"],
            "poles_erected": day["poles_erected"],
            "new_poles": day["new_poles"],
            "old_poles": day["old_poles"],
            "dtrs_erected": day["dtrs_erected"],
            "span_meters": round(day["span_meters"], 2),
            "photos_count": day["photos_count"]
        })

    valid_dates = [d["raw_date"] for d in sorted_days if d["raw_date"]]
    total_working_days = len(day_progress_list)
    if valid_dates:
        min_date = min(valid_dates)
        max_date = max(valid_dates)
        total_calendar_days = (max_date - min_date).days + 1
        start_date_str = min_date.strftime('%Y-%m-%d')
        completion_date_str = max_date.strftime('%Y-%m-%d')
    else:
        total_calendar_days = total_working_days or 1
        start_date_str = None
        completion_date_str = None

    pole_nodes = [n for n in nodes_data if n["node_type"] == "POLE"]
    dtr_nodes = [n for n in nodes_data if n["node_type"] == "DTR"]
    new_pole_nodes = [n for n in pole_nodes if n["is_new_pole"]]
    old_pole_nodes = [n for n in pole_nodes if not n["is_new_pole"]]

    material_summary = {
        "total_poles": len(pole_nodes),
        "new_poles_count": len(new_pole_nodes),
        "old_poles_count": len(old_pole_nodes),
        "total_dtr": len(dtr_nodes),
        "total_route_length_meters": round(total_route_distance, 2),
        "total_earthing": sum(n["earthing_quantity"] for n in nodes_data),
        "total_stay_sets": sum(n["stay_set_quantity"] for n in nodes_data),
        "total_dead_end_clamps": sum(n["dead_end_clamp_qty"] for n in nodes_data),
        "total_suspension_clamps": sum(n["suspension_clamp_qty"] for n in nodes_data),
        "total_pole_clamps": sum(n["pole_clamp_qty"] for n in nodes_data),
        "total_ipc": sum(n["ipc_qty"] for n in nodes_data),
        "total_service_connections": sum(n["service_connection_qty"] for n in nodes_data),
        "total_extra_consumption": sum(n["extra_consumption"] for n in nodes_data),
        "total_pole_qty": sum(n["pole_qty"] for n in pole_nodes),
        "conductor_names": list(conductor_names_set) or ["Standard ACSR / AB Cable"],
        "pole_db_summary": pole_db_summary,
        "total_pole_db": sum(pole_db_summary.values())
    }

    response_data = {
        "Code": "SUCCESS001",
        "Message": "Erection Execution Details Fetched Successfully",
        "Data": {
            "id": erection.id,
            "feeder_name": erection.feeder_name,
            "dtr_code": erection.dtr_code,
            "drawing_no": erection.drawing_no,
            "state_id": erection.state_id,
            "state_name": state_map.get(erection.state_id),
            "district_id": erection.district_id,
            "district_name": district_map.get(erection.district_id),
            "block_id": erection.block_id,
            "block_name": block_map.get(erection.block_id),
            "village_id": erection.village_id,
            "village_name": village_map.get(erection.village_id),
            "contractor_id": erection.contractor_id,
            "contractor_name": contractor_map.get(erection.contractor_id) or "Unassigned",
            "surveyor_id": erection.surveyor_id,
            "surveyor_name": surveyor_map.get(erection.surveyor_id, "Unassigned"),
            "surveyor_phone": surveyor_phone_map.get(erection.surveyor_id, ""),
            "surveyor_email": surveyor_email_map.get(erection.surveyor_id, ""),
            "type_of_work": erection.type_of_work,
            "type_of_work_name": tow_info.get('value') or "Erection Work",
            "lt_starting_point": erection.lt_starting_point,
            "lt_starting_point_name": ltsp_info.get('value') or "Substation",
            "remarks": erection.remarks,
            "status": erection.status,
            "status_label": "Completed" if erection.status == 2 else "Active",
            "created_on": erection.created_on.strftime('%Y-%m-%d %H:%M:%S') if erection.created_on else None,
            "updated_on": erection.updated_on.strftime('%Y-%m-%d %H:%M:%S') if erection.updated_on else None,
            "nodes_count": len(nodes_data),
            "pole_count": len(pole_nodes),
            "dtr_count": len(dtr_nodes),
            "material_summary": material_summary,
            "day_wise_progress": day_progress_list,
            "progress_summary": {
                "total_working_days": total_working_days,
                "total_calendar_days": total_calendar_days,
                "start_date": start_date_str,
                "completion_date": completion_date_str
            },
            "nodes": nodes_data
        }
    }
    logger.warning('================================== END - Get Erection Detail =================================')
    return JsonResponse(response_data)


@csrf_exempt
@require_post
def list_survey_lines(request):
    logger.warning('================================== START - Survey Line List =================================')
    payload = getattr(request, 'data', {}) or {}
    
    # Query mappings for locations
    state_map = {s.id: s.state_name for s in StateMaster.objects.all()}
    district_map = {d.id: d.district_name for d in DistrictMaster.objects.all()}
    block_map = {b.id: b.block_name for b in BlockMaster.objects.all()}

    queryset = SurveyLine.objects.all().order_by('-updated_on')
    
    # Search filter
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(
            Q(contractor_name__icontains=search) |
            Q(line_type__icontains=search) |
            Q(feeder_name__icontains=search) |
            Q(surveyor__username__icontains=search) |
            Q(surveyor__email__icontains=search)
        )
        
    # 1. State filter
    state_id = payload.get('state_id') or payload.get('state')
    if state_id is not None and str(state_id).strip() != '' and str(state_id).lower() != 'all':
        try:
            queryset = queryset.filter(state_id=int(state_id))
        except (ValueError, TypeError):
            pass

    # 2. District filter (handling distrct typo as well)
    district_id = payload.get('district_id') or payload.get('distrct_id') or payload.get('district')
    if district_id is not None and str(district_id).strip() != '' and str(district_id).lower() != 'all':
        try:
            queryset = queryset.filter(district_id=int(district_id))
        except (ValueError, TypeError):
            pass

    # 3. Block filter
    block_id = payload.get('block_id') or payload.get('block')
    if block_id is not None and str(block_id).strip() != '' and str(block_id).lower() != 'all':
        try:
            queryset = queryset.filter(block_id=int(block_id))
        except (ValueError, TypeError):
            pass

    # 4. Feeder filter
    feeder = payload.get('feeder') or payload.get('feeder_name')
    if feeder is not None and str(feeder).strip() != '' and str(feeder).lower() != 'all':
        queryset = queryset.filter(feeder_name__icontains=str(feeder).strip())

    # 5. Contractor filter (by name or ID)
    contractor = payload.get('contractor_name') or payload.get('contractor_id') or payload.get('contractor')
    if contractor is not None and str(contractor).strip() != '' and str(contractor).lower() != 'all':
        contractor_str = str(contractor).strip()
        if contractor_str.isdigit():
            c_obj = ContractorMaster.objects.filter(id=int(contractor_str)).first()
            if c_obj:
                queryset = queryset.filter(Q(contractor_name__icontains=c_obj.contractor_name) | Q(contractor_name__icontains=contractor_str))
            else:
                queryset = queryset.filter(contractor_name__icontains=contractor_str)
        else:
            queryset = queryset.filter(contractor_name__icontains=contractor_str)

    # 6. Line type filter
    line_type = payload.get('line_type')
    if line_type and str(line_type).strip() != '' and str(line_type).upper() != 'ALL':
        line_type_str = str(line_type).strip()
        queryset = queryset.filter(Q(line_type=line_type_str) | Q(line_type__icontains=line_type_str))

    # Sync status filter
    is_synced = payload.get('is_synced')
    if is_synced is not None and str(is_synced).lower() != 'all':
        is_synced_val = str(is_synced).lower() in ['true', '1', 'yes']
        queryset = queryset.filter(is_synced=is_synced_val)
        
    # 7. Status filter
    status = payload.get('status')
    if status is not None and str(status).strip() != '' and str(status).lower() != 'all':
        try:
            queryset = queryset.filter(status=int(status))
        except (ValueError, TypeError):
            pass
            
    # Surveyor filter
    surveyor_id = payload.get('surveyor_id')
    if surveyor_id:
        queryset = queryset.filter(surveyor_id=surveyor_id)

    # 8. Start Date and End Date filters (on created_on)
    start_date = payload.get('start_date') or payload.get('from_date')
    if start_date and str(start_date).strip() != '':
        try:
            from datetime import datetime
            start_d = datetime.strptime(str(start_date)[:10], '%Y-%m-%d').date()
            queryset = queryset.filter(created_on__date__gte=start_d)
        except Exception as e:
            logger.warning(f"Error parsing start_date {start_date}: {e}")

    end_date = payload.get('end_date') or payload.get('to_date')
    if end_date and str(end_date).strip() != '':
        try:
            from datetime import datetime
            end_d = datetime.strptime(str(end_date)[:10], '%Y-%m-%d').date()
            queryset = queryset.filter(created_on__date__lte=end_d)
        except Exception as e:
            logger.warning(f"Error parsing end_date {end_date}: {e}")
        
    total_count = queryset.count()
    
    # 9 & 10. Page size and Page index (mandatory for pagination --- if null send all data)
    raw_page_size = payload.get('page_size')
    if raw_page_size is None:
        raw_page_size = payload.get('pageSize')

    raw_page_index = payload.get('page_index')
    if raw_page_index is None:
        raw_page_index = payload.get('pageIndex')
    if raw_page_index is None:
        raw_page_index = payload.get('page_no')

    # Check if either page_size or page_index is omitted or null -> return all data
    is_all_data = False
    if raw_page_size in [None, '', 'null', 'None', 'all', 'ALL'] or raw_page_index in [None, '', 'null', 'None', 'all', 'ALL']:
        is_all_data = True
        page_size = None
        page_index = 1
    else:
        try:
            page_size = int(raw_page_size)
            page_index = int(raw_page_index)
            if page_size <= 0:
                is_all_data = True
                page_size = None
                page_index = 1
            elif page_index < 1:
                page_index = 1
        except (ValueError, TypeError):
            is_all_data = True
            page_size = None
            page_index = 1

    if is_all_data or page_size is None:
        paginated_items = queryset
        total_pages = 1
        current_page = 1
        returned_page_size = total_count
    else:
        offset = (page_index - 1) * page_size
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
        paginated_items = queryset[offset:offset + page_size]
        current_page = page_index
        returned_page_size = page_size

    line_type_dict = dict(SurveyLine.LINE_TYPES)
    
    data_list = []
    for item in paginated_items:
        nodes_qs = item.nodes.all().order_by('sequence_number')
        data_list.append({
            "id": item.id,
            "contractor_name": item.contractor_name or "N/A",
            "line_type": item.line_type,
            "line_type_display": line_type_dict.get(item.line_type, item.line_type),
            "state_id": item.state_id,
            "state_name": state_map.get(item.state_id),
            "district_id": item.district_id,
            "district_name": district_map.get(item.district_id),
            "block_id": item.block_id,
            "block_name": block_map.get(item.block_id),
            "feeder_name": item.feeder_name,
            "surveyor_id": item.surveyor_id,
            "surveyor_name": item.surveyor.username if item.surveyor else "Unassigned",
            "surveyor_phone": item.surveyor.phone if item.surveyor else "",
            "is_synced": item.is_synced,
            "status": item.status,
            "status_label": "Active" if item.status == 1 else "Archived",
            "nodes_count": nodes_qs.count(),
            "created_on": item.created_on.strftime('%Y-%m-%d %H:%M:%S') if item.created_on else None,
            "updated_on": item.updated_on.strftime('%Y-%m-%d %H:%M:%S') if item.updated_on else None,
            "nodes": [
                {
                    "id": n.id,
                    "node_type": n.node_type,
                    "sequence_number": n.sequence_number,
                    "name_label": n.name_label,
                    "latitude": float(n.latitude),
                    "longitude": float(n.longitude),
                    "attributes": n.attributes,
                    "image_path": n.image_path,
                    "parent_label": n.parent_label,
                    "captured_at": n.captured_at.strftime('%Y-%m-%d %H:%M:%S') if n.captured_at else None,
                }
                for n in nodes_qs
            ]
        })
        
    response_data = {
        "Code": "SUCCESS001",
        "Message": "Survey Lines Fetched Successfully",
        "Data": data_list,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": current_page,
        "page_index": current_page,
        "page_size": returned_page_size
    }
    logger.warning('================================== END - Survey Line List =================================')
    return JsonResponse(response_data)


@csrf_exempt
@require_post
def get_survey_line_detail(request):
    logger.warning('================================== START - Get Survey Line Detail =================================')
    payload = getattr(request, 'data', {}) or {}
    survey_id = payload.get('id') or payload.get('survey_line_id')
    if not survey_id:
        return JsonResponse({"Exception": True, "Message": "Survey ID is required"}, status=400)
        
    survey = SurveyLine.objects.filter(id=survey_id).first()
    if not survey:
        return JsonResponse({"Exception": True, "Message": "Survey record not found"}, status=404)
        
    state_map = {s.id: s.state_name for s in StateMaster.objects.all()}
    district_map = {d.id: d.district_name for d in DistrictMaster.objects.all()}
    block_map = {b.id: b.block_name for b in BlockMaster.objects.all()}

    line_type_dict = dict(SurveyLine.LINE_TYPES)
    nodes = []
    prev_node = None
    total_route_distance = 0.0
    day_groups = {}
    conductor_names_set = set()

    for node in survey.nodes.all().order_by('sequence_number'):
        node_imgs = extract_node_images(node)
        is_new = check_is_new_pole(node)
        
        if prev_node:
            dist_to_prev = calculate_haversine_distance(
                prev_node.latitude, prev_node.longitude,
                node.latitude, node.longitude
            )
        else:
            dist_to_prev = 0.0
            
        total_route_distance += dist_to_prev
        prev_node = node
        
        attrs = node.attributes or {}
        cable = attrs.get('cableSize')
        if cable:
            conductor_names_set.add(str(cable))

        node_dict = {
            "id": node.id,
            "node_type": node.node_type,
            "sequence_number": node.sequence_number,
            "name_label": node.name_label,
            "latitude": float(node.latitude),
            "longitude": float(node.longitude),
            "distance_to_prev_meters": dist_to_prev,
            "cumulative_distance_meters": round(total_route_distance, 2),
            "is_new_pole": is_new,
            "structure_condition": "NEW" if is_new else "OLD",
            "structure_condition_label": "New Pole" if (node.node_type == 'POLE' and is_new) else ("Old Pole" if node.node_type == 'POLE' else "DTR"),
            "attributes": attrs,
            "image_path": node.image_path,
            "images": node_imgs,
            "parent_label": node.parent_label,
            "captured_at": node.captured_at.strftime('%Y-%m-%d %H:%M:%S') if node.captured_at else None,
        }
        nodes.append(node_dict)

        node_dt = node.captured_at or node.created_on
        date_key = node_dt.strftime('%Y-%m-%d') if node_dt else 'Survey Entry'
        if date_key not in day_groups:
            day_groups[date_key] = {
                "date": date_key,
                "raw_date": node_dt.date() if node_dt else None,
                "nodes": [],
                "poles_count": 0,
                "dtrs_count": 0,
                "span_meters": 0.0,
                "photos_count": 0,
                "materials": {}
            }
        dg = day_groups[date_key]
        dg["nodes"].append(node_dict)
        if node.node_type == 'POLE':
            dg["poles_count"] += 1
        elif node.node_type == 'DTR':
            dg["dtrs_count"] += 1
        dg["span_meters"] += dist_to_prev
        dg["photos_count"] += len(node_imgs)

    sorted_days = sorted(day_groups.values(), key=lambda x: x["date"])
    day_progress_list = []
    for idx, day in enumerate(sorted_days, 1):
        summary_parts = []
        if day["dtrs_count"] > 0:
            summary_parts.append(f"{day['dtrs_count']} DTR surveyed")
        if day["poles_count"] > 0:
            summary_parts.append(f"{day['poles_count']} Pole(s) surveyed")
        day_progress_list.append({
            "day_number": idx,
            "date": day["date"],
            "nodes_count": len(day["nodes"]),
            "nodes_summary": [f"{n['name_label']} ({n['structure_condition_label']})" for n in day["nodes"]],
            "work_description": ", ".join(summary_parts) if summary_parts else "Survey line mapping",
            "materials_summary": f"{day['poles_count']} Poles, {day['dtrs_count']} DTRs mapped",
            "materials": {},
            "poles_erected": day["poles_count"],
            "new_poles": sum(1 for n in day["nodes"] if n.get("is_new_pole")),
            "old_poles": sum(1 for n in day["nodes"] if not n.get("is_new_pole")),
            "dtrs_erected": day["dtrs_count"],
            "span_meters": round(day["span_meters"], 2),
            "photos_count": day["photos_count"]
        })

    valid_dates = [d["raw_date"] for d in sorted_days if d["raw_date"]]
    total_working_days = len(day_progress_list)
    if valid_dates:
        min_date = min(valid_dates)
        max_date = max(valid_dates)
        total_calendar_days = (max_date - min_date).days + 1
        start_date_str = min_date.strftime('%Y-%m-%d')
        completion_date_str = max_date.strftime('%Y-%m-%d')
    else:
        total_calendar_days = total_working_days or 1
        start_date_str = None
        completion_date_str = None

    pole_count = sum(1 for n in nodes if n["node_type"] == "POLE")
    dtr_count = sum(1 for n in nodes if n["node_type"] == "DTR")
    
    material_summary = {
        "total_poles": pole_count,
        "new_poles_count": sum(1 for n in nodes if n["node_type"] == "POLE" and n.get("is_new_pole")),
        "old_poles_count": sum(1 for n in nodes if n["node_type"] == "POLE" and not n.get("is_new_pole")),
        "total_dtr": dtr_count,
        "total_route_length_meters": round(total_route_distance, 2),
        "conductor_names": list(conductor_names_set) or [line_type_dict.get(survey.line_type, survey.line_type)],
        "line_type": survey.line_type,
        "line_type_display": line_type_dict.get(survey.line_type, survey.line_type)
    }

    response_data = {
        "Code": "SUCCESS001",
        "Message": "Survey Line Details Fetched Successfully",
        "Data": {
            "id": survey.id,
            "contractor_name": survey.contractor_name or "N/A",
            "line_type": survey.line_type,
            "line_type_display": line_type_dict.get(survey.line_type, survey.line_type),
            "state_id": survey.state_id,
            "state_name": state_map.get(survey.state_id),
            "district_id": survey.district_id,
            "district_name": district_map.get(survey.district_id),
            "block_id": survey.block_id,
            "block_name": block_map.get(survey.block_id),
            "feeder_name": survey.feeder_name,
            "surveyor_id": survey.surveyor_id,
            "surveyor_name": survey.surveyor.username if survey.surveyor else "Unassigned",
            "surveyor_phone": survey.surveyor.phone if survey.surveyor else "",
            "surveyor_email": survey.surveyor.email if survey.surveyor else "",
            "is_synced": survey.is_synced,
            "status": survey.status,
            "status_label": "Active" if survey.status == 1 else "Archived",
            "nodes_count": len(nodes),
            "pole_count": pole_count,
            "dtr_count": dtr_count,
            "material_summary": material_summary,
            "day_wise_progress": day_progress_list,
            "progress_summary": {
                "total_working_days": total_working_days,
                "total_calendar_days": total_calendar_days,
                "start_date": start_date_str,
                "completion_date": completion_date_str
            },
            "created_on": survey.created_on.strftime('%Y-%m-%d %H:%M:%S') if survey.created_on else None,
            "updated_on": survey.updated_on.strftime('%Y-%m-%d %H:%M:%S') if survey.updated_on else None,
            "nodes": nodes
        }
    }
    logger.warning('================================== END - Get Survey Line Detail =================================')
    return JsonResponse(response_data)

