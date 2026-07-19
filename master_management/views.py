import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from exception import (
    MandatoryInputMissingException, UserAlreadyExistException, UserNotFoundException
)
from commonUtility.decorators import require_post
from commonUtility.utils import mandatoryInputCheck
from common.models import AuditLog
from master_management.models import StateMaster, DistrictMaster, BlockMaster, RoleMaster, DesignationMaster, ConductorMaster, PoleMaster, TransformerMaster

logger = logging.getLogger('master_management')

@csrf_exempt
@require_post
def add_state(request):
    """
    POST Request:
    {
        "state_code": "ST01",
        "state_name": "State Name"
    }
    """
    logger.warning('================================== START - Add State =================================')
    payload = request.data
    logger.info(f'Received add state payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["state_code", "state_name"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    state_code = str(payload.get('state_code')).strip()
    state_name = str(payload.get('state_name')).strip()

    if not state_code or not state_name:
        raise MandatoryInputMissingException("state_code and state_name cannot be empty strings.")

    # Check for duplicate state_code or state_name
    duplicate = StateMaster.objects.filter(
        Q(state_code__iexact=state_code) | Q(state_name__iexact=state_name)
    ).first()

    if duplicate:
        if duplicate.state_code.lower() == state_code.lower():
            raise UserAlreadyExistException(f"State Code '{state_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"State Name '{state_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create State
    state = StateMaster.objects.create(
        state_code=state_code,
        state_name=state_name,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='state_master',
        operation='INSERT',
        ref_id=state.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"State created: {state.state_name} ({state.state_code})"
    )

    logger.warning('================================== END - Add State =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "State created successfully.",
        "state_id": state.id
    })


@csrf_exempt
@require_post
def edit_state(request):
    """
    POST Request:
    {
        "id": 1,
        "state_code": "ST01-Updated",
        "state_name": "State Name Updated",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit State =================================')
    payload = request.data
    logger.info(f'Received edit state payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    state_id = payload.get('id')
    state = StateMaster.objects.filter(id=state_id).first()
    if not state:
        raise UserNotFoundException(f"State with ID {state_id} not found.")

    # Store original values for Audit log
    old_data = {
        "state_code": state.state_code,
        "state_name": state.state_name,
        "is_active": state.is_active
    }

    updated = False
    state_code = payload.get('state_code')
    state_name = payload.get('state_name')
    is_active = payload.get('is_active')

    # Update state_code if provided
    if state_code is not None:
        state_code = str(state_code).strip()
        if not state_code:
            raise MandatoryInputMissingException("state_code cannot be empty.")
        # Check uniqueness excluding current record
        if StateMaster.objects.filter(state_code__iexact=state_code).exclude(id=state.id).exists():
            raise UserAlreadyExistException(f"State Code '{state_code}' already exists.")
        if state.state_code != state_code:
            state.state_code = state_code
            updated = True

    # Update state_name if provided
    if state_name is not None:
        state_name = str(state_name).strip()
        if not state_name:
            raise MandatoryInputMissingException("state_name cannot be empty.")
        # Check uniqueness excluding current record
        if StateMaster.objects.filter(state_name__iexact=state_name).exclude(id=state.id).exists():
            raise UserAlreadyExistException(f"State Name '{state_name}' already exists.")
        if state.state_name != state_name:
            state.state_name = state_name
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if state.is_active != is_active_val:
            state.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if any updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        state.updated_by = user_id
        state.save()

        AuditLog.objects.create(
            table_name='state_master',
            operation='UPDATE',
            ref_id=state.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"State updated: {state.state_name} ({state.state_code})"
        )

    logger.warning('================================== END - Edit State =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "State updated successfully."
    })


@csrf_exempt
def list_states(request):
    """
    GET / POST Request:
    Supports filtering by search query and is_active status.
    """
    logger.warning('================================== START - List States =================================')
    payload = request.data
    logger.info(f'Received list states params: {payload}')

    queryset = StateMaster.objects.all()

    # Search filter (matches state_code or state_name)
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(Q(state_code__icontains=search) | Q(state_name__icontains=search))

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    # Order alphabetically by state name
    queryset = queryset.order_by('state_name')

    states_list = []
    for state in queryset:
        states_list.append({
            "id": state.id,
            "state_code": state.state_code,
            "state_name": state.state_name,
            "is_active": state.is_active,
            "created_on": state.created_on.strftime('%Y-%m-%d %H:%M:%S') if state.created_on else None,
            "updated_on": state.updated_on.strftime('%Y-%m-%d %H:%M:%S') if state.updated_on else None,
        })

    logger.warning('================================== END - List States =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "States retrieved successfully.",
        "states": states_list
    })


@csrf_exempt
def get_state_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get State Detail =================================')
    payload = request.data
    logger.info(f'Received get state detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    state_id = payload.get('id')
    state = StateMaster.objects.filter(id=state_id).first()
    if not state:
        raise UserNotFoundException(f"State with ID {state_id} not found.")

    logger.warning('================================== END - Get State Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "State detail retrieved successfully.",
        "state": {
            "id": state.id,
            "state_code": state.state_code,
            "state_name": state.state_name,
            "is_active": state.is_active,
            "created_by": state.created_by,
            "created_on": state.created_on.strftime('%Y-%m-%d %H:%M:%S') if state.created_on else None,
            "updated_by": state.updated_by,
            "updated_on": state.updated_on.strftime('%Y-%m-%d %H:%M:%S') if state.updated_on else None,
        }
    })


@csrf_exempt
@require_post
def add_district(request):
    """
    POST Request:
    {
        "state_id": 1,
        "district_code": "DST01",
        "district_name": "District Name"
    }
    """
    logger.warning('================================== START - Add District =================================')
    payload = request.data
    logger.info(f'Received add district payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["state_id", "district_code", "district_name"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    state_id = payload.get('state_id')
    district_code = str(payload.get('district_code')).strip()
    district_name = str(payload.get('district_name')).strip()

    if not district_code or not district_name:
        raise MandatoryInputMissingException("district_code and district_name cannot be empty strings.")

    # Check if State exists
    state = StateMaster.objects.filter(id=state_id).first()
    if not state:
        raise UserNotFoundException(f"State with ID {state_id} not found.")

    # Check for duplicates
    duplicate = DistrictMaster.objects.filter(
        Q(district_code__iexact=district_code) | Q(district_name__iexact=district_name)
    ).first()

    if duplicate:
        if duplicate.district_code.lower() == district_code.lower():
            raise UserAlreadyExistException(f"District Code '{district_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"District Name '{district_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create District
    district = DistrictMaster.objects.create(
        state=state,
        district_code=district_code,
        district_name=district_name,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='district_master',
        operation='INSERT',
        ref_id=district.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"District created: {district.district_name} ({district.district_code}) under State: {state.state_name}"
    )

    logger.warning('================================== END - Add District =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "District created successfully.",
        "district_id": district.id
    })


@csrf_exempt
@require_post
def edit_district(request):
    """
    POST Request:
    {
        "id": 1,
        "state_id": 2,
        "district_code": "DST01-Updated",
        "district_name": "District Name Updated",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit District =================================')
    payload = request.data
    logger.info(f'Received edit district payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    district_id = payload.get('id')
    district = DistrictMaster.objects.filter(id=district_id).first()
    if not district:
        raise UserNotFoundException(f"District with ID {district_id} not found.")

    # Store original values for Audit log
    old_data = {
        "state_id": district.state.id,
        "district_code": district.district_code,
        "district_name": district.district_name,
        "is_active": district.is_active
    }

    updated = False
    state_id = payload.get('state_id')
    district_code = payload.get('district_code')
    district_name = payload.get('district_name')
    is_active = payload.get('is_active')

    # Update state_id if provided
    if state_id is not None:
        state = StateMaster.objects.filter(id=state_id).first()
        if not state:
            raise UserNotFoundException(f"State with ID {state_id} not found.")
        if district.state.id != state.id:
            district.state = state
            updated = True

    # Update district_code if provided
    if district_code is not None:
        district_code = str(district_code).strip()
        if not district_code:
            raise MandatoryInputMissingException("district_code cannot be empty.")
        # Check uniqueness excluding current record
        if DistrictMaster.objects.filter(district_code__iexact=district_code).exclude(id=district.id).exists():
            raise UserAlreadyExistException(f"District Code '{district_code}' already exists.")
        if district.district_code != district_code:
            district.district_code = district_code
            updated = True

    # Update district_name if provided
    if district_name is not None:
        district_name = str(district_name).strip()
        if not district_name:
            raise MandatoryInputMissingException("district_name cannot be empty.")
        # Check uniqueness excluding current record
        if DistrictMaster.objects.filter(district_name__iexact=district_name).exclude(id=district.id).exists():
            raise UserAlreadyExistException(f"District Name '{district_name}' already exists.")
        if district.district_name != district_name:
            district.district_name = district_name
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if district.is_active != is_active_val:
            district.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if any updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        district.updated_by = user_id
        district.save()

        AuditLog.objects.create(
            table_name='district_master',
            operation='UPDATE',
            ref_id=district.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"District updated: {district.district_name} ({district.district_code})"
        )

    logger.warning('================================== END - Edit District =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "District updated successfully."
    })


@csrf_exempt
def list_districts(request):
    """
    GET / POST Request:
    Supports filtering by state_id, search query, and is_active status.
    """
    logger.warning('================================== START - List Districts =================================')
    payload = request.data
    logger.info(f'Received list districts params: {payload}')

    # Fetch districts, prefetch state to avoid N+1 queries
    queryset = DistrictMaster.objects.select_related('state').all()

    # Filter by state_id
    state_id = payload.get('state_id')
    if state_id is not None:
        queryset = queryset.filter(state_id=state_id)

    # Search filter (matches district_code or district_name)
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(Q(district_code__icontains=search) | Q(district_name__icontains=search))

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    # Order alphabetically by district name
    queryset = queryset.order_by('district_name')

    districts_list = []
    for district in queryset:
        districts_list.append({
            "id": district.id,
            "state_id": district.state.id,
            "state_name": district.state.state_name,
            "district_code": district.district_code,
            "district_name": district.district_name,
            "is_active": district.is_active,
            "created_on": district.created_on.strftime('%Y-%m-%d %H:%M:%S') if district.created_on else None,
            "updated_on": district.updated_on.strftime('%Y-%m-%d %H:%M:%S') if district.updated_on else None,
        })

    logger.warning('================================== END - List Districts =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Districts retrieved successfully.",
        "districts": districts_list
    })


@csrf_exempt
def get_district_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get District Detail =================================')
    payload = request.data
    logger.info(f'Received get district detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    district_id = payload.get('id')
    district = DistrictMaster.objects.select_related('state').filter(id=district_id).first()
    if not district:
        raise UserNotFoundException(f"District with ID {district_id} not found.")

    logger.warning('================================== END - Get District Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "District detail retrieved successfully.",
        "district": {
            "id": district.id,
            "state_id": district.state.id,
            "state_name": district.state.state_name,
            "district_code": district.district_code,
            "district_name": district.district_name,
            "is_active": district.is_active,
            "created_by": district.created_by,
            "created_on": district.created_on.strftime('%Y-%m-%d %H:%M:%S') if district.created_on else None,
            "updated_by": district.updated_by,
            "updated_on": district.updated_on.strftime('%Y-%m-%d %H:%M:%S') if district.updated_on else None,
        }
    })


@csrf_exempt
@require_post
def add_block(request):
    """
    POST Request:
    {
        "state_id": 1,
        "district_id": 1,
        "block_code": "BLK01",
        "block_name": "Block Name"
    }
    """
    logger.warning('================================== START - Add Block =================================')
    payload = request.data
    logger.info(f'Received add block payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["state_id", "district_id", "block_code", "block_name"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    state_id = payload.get('state_id')
    district_id = payload.get('district_id')
    block_code = str(payload.get('block_code')).strip()
    block_name = str(payload.get('block_name')).strip()

    if not block_code or not block_name:
        raise MandatoryInputMissingException("block_code and block_name cannot be empty strings.")

    # Check if State exists
    state = StateMaster.objects.filter(id=state_id).first()
    if not state:
        raise UserNotFoundException(f"State with ID {state_id} not found.")

    # Check if District exists
    district = DistrictMaster.objects.filter(id=district_id).first()
    if not district:
        raise UserNotFoundException(f"District with ID {district_id} not found.")

    # Verify District belongs to State
    if district.state.id != state.id:
        raise MandatoryInputMissingException(f"District with ID {district_id} does not belong to State with ID {state_id}.")

    # Check for duplicates
    duplicate = BlockMaster.objects.filter(
        Q(block_code__iexact=block_code) | Q(block_name__iexact=block_name)
    ).first()

    if duplicate:
        if duplicate.block_code.lower() == block_code.lower():
            raise UserAlreadyExistException(f"Block Code '{block_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"Block Name '{block_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create Block
    block = BlockMaster.objects.create(
        state=state,
        district=district,
        block_code=block_code,
        block_name=block_name,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='block_master',
        operation='INSERT',
        ref_id=block.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"Block created: {block.block_name} ({block.block_code}) under District: {district.district_name}, State: {state.state_name}"
    )

    logger.warning('================================== END - Add Block =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Block created successfully.",
        "block_id": block.id
    })


@csrf_exempt
@require_post
def edit_block(request):
    """
    POST Request:
    {
        "id": 1,
        "state_id": 2,
        "district_id": 2,
        "block_code": "BLK01-Updated",
        "block_name": "Block Name Updated",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit Block =================================')
    payload = request.data
    logger.info(f'Received edit block payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    block_id = payload.get('id')
    block = BlockMaster.objects.filter(id=block_id).first()
    if not block:
        raise UserNotFoundException(f"Block with ID {block_id} not found.")

    # Store original values for Audit log
    old_data = {
        "state_id": block.state.id,
        "district_id": block.district.id,
        "block_code": block.block_code,
        "block_name": block.block_name,
        "is_active": block.is_active
    }

    updated = False
    state_id = payload.get('state_id')
    district_id = payload.get('district_id')
    block_code = payload.get('block_code')
    block_name = payload.get('block_name')
    is_active = payload.get('is_active')

    # Resolve state and district changes
    target_state = block.state
    target_district = block.district

    if state_id is not None:
        target_state = StateMaster.objects.filter(id=state_id).first()
        if not target_state:
            raise UserNotFoundException(f"State with ID {state_id} not found.")
        if block.state.id != target_state.id:
            block.state = target_state
            updated = True

    if district_id is not None:
        target_district = DistrictMaster.objects.filter(id=district_id).first()
        if not target_district:
            raise UserNotFoundException(f"District with ID {district_id} not found.")
        if block.district.id != target_district.id:
            block.district = target_district
            updated = True

    # If state or district is updated, ensure they remain logically linked
    if updated or state_id is not None or district_id is not None:
        if target_district.state.id != target_state.id:
            raise MandatoryInputMissingException(f"District with ID {target_district.id} does not belong to State with ID {target_state.id}.")

    # Update block_code if provided
    if block_code is not None:
        block_code = str(block_code).strip()
        if not block_code:
            raise MandatoryInputMissingException("block_code cannot be empty.")
        # Check uniqueness excluding current record
        if BlockMaster.objects.filter(block_code__iexact=block_code).exclude(id=block.id).exists():
            raise UserAlreadyExistException(f"Block Code '{block_code}' already exists.")
        if block.block_code != block_code:
            block.block_code = block_code
            updated = True

    # Update block_name if provided
    if block_name is not None:
        block_name = str(block_name).strip()
        if not block_name:
            raise MandatoryInputMissingException("block_name cannot be empty.")
        # Check uniqueness excluding current record
        if BlockMaster.objects.filter(block_name__iexact=block_name).exclude(id=block.id).exists():
            raise UserAlreadyExistException(f"Block Name '{block_name}' already exists.")
        if block.block_name != block_name:
            block.block_name = block_name
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if block.is_active != is_active_val:
            block.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        block.updated_by = user_id
        block.save()

        AuditLog.objects.create(
            table_name='block_master',
            operation='UPDATE',
            ref_id=block.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"Block updated: {block.block_name} ({block.block_code})"
        )

    logger.warning('================================== END - Edit Block =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Block updated successfully."
    })


@csrf_exempt
def list_blocks(request):
    """
    GET / POST Request:
    Supports filtering by state_id, district_id, search query, and is_active status.
    """
    logger.warning('================================== START - List Blocks =================================')
    payload = request.data
    logger.info(f'Received list blocks params: {payload}')

    # Fetch blocks, prefetching foreign models
    queryset = BlockMaster.objects.select_related('state', 'district').all()

    # Filter by state_id
    state_id = payload.get('state_id')
    if state_id is not None:
        queryset = queryset.filter(state_id=state_id)

    # Filter by district_id
    district_id = payload.get('district_id')
    if district_id is not None:
        queryset = queryset.filter(district_id=district_id)

    # Search filter (matches block_code or block_name)
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(Q(block_code__icontains=search) | Q(block_name__icontains=search))

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    # Order alphabetically by block name
    queryset = queryset.order_by('block_name')

    # Total Count matching the filters
    total_count = queryset.count()

    # Pagination parameters
    try:
        page_no = int(payload.get('page_no', 1))
        if page_no < 1:
            page_no = 1
    except (ValueError, TypeError):
        page_no = 1

    try:
        page_size = int(payload.get('page_size', 10))
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    offset = (page_no - 1) * page_size
    limit = page_size

    # Slice queryset for pagination
    queryset = queryset[offset:offset + limit]
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    blocks_list = []
    for block in queryset:
        blocks_list.append({
            "id": block.id,
            "state_id": block.state.id,
            "state_name": block.state.state_name,
            "district_id": block.district.id,
            "district_name": block.district.district_name,
            "block_code": block.block_code,
            "block_name": block.block_name,
            "is_active": block.is_active,
            "created_on": block.created_on.strftime('%Y-%m-%d %H:%M:%S') if block.created_on else None,
            "updated_on": block.updated_on.strftime('%Y-%m-%d %H:%M:%S') if block.updated_on else None,
        })

    logger.warning('================================== END - List Blocks =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Blocks retrieved successfully.",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page_no,
        "page_size": page_size,
        "blocks": blocks_list
    })


@csrf_exempt
def get_block_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get Block Detail =================================')
    payload = request.data
    logger.info(f'Received get block detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    block_id = payload.get('id')
    block = BlockMaster.objects.select_related('state', 'district').filter(id=block_id).first()
    if not block:
        raise UserNotFoundException(f"Block with ID {block_id} not found.")

    logger.warning('================================== END - Get Block Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Block detail retrieved successfully.",
        "block": {
            "id": block.id,
            "state_id": block.state.id,
            "state_name": block.state.state_name,
            "district_id": block.district.id,
            "district_name": block.district.district_name,
            "block_code": block.block_code,
            "block_name": block.block_name,
            "is_active": block.is_active,
            "created_by": block.created_by,
            "created_on": block.created_on.strftime('%Y-%m-%d %H:%M:%S') if block.created_on else None,
            "updated_by": block.updated_by,
            "updated_on": block.updated_on.strftime('%Y-%m-%d %H:%M:%S') if block.updated_on else None,
        }
    })


@csrf_exempt
@require_post
def add_role(request):
    """
    POST Request:
    {
        "role_name": "Field Level Surveyor",
        "role_code": "FIELD_SURVEYOR",
        "description": "Field level surveyor role"
    }
    """
    logger.warning('================================== START - Add Role =================================')
    payload = request.data
    logger.info(f'Received add role payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["role_name", "role_code"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    role_name = str(payload.get('role_name')).strip()
    role_code = str(payload.get('role_code')).strip()
    description = payload.get('description')

    if not role_name or not role_code:
        raise MandatoryInputMissingException("role_name and role_code cannot be empty strings.")

    # Check for duplicates
    duplicate = RoleMaster.objects.filter(
        Q(role_name__iexact=role_name) | Q(role_code__iexact=role_code)
    ).first()

    if duplicate:
        if duplicate.role_code.lower() == role_code.lower():
            raise UserAlreadyExistException(f"Role Code '{role_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"Role Name '{role_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create Role
    role = RoleMaster.objects.create(
        role_name=role_name,
        role_code=role_code,
        description=description,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='role_master',
        operation='INSERT',
        ref_id=role.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"Role created: {role.role_name} ({role.role_code})"
    )

    logger.warning('================================== END - Add Role =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Role created successfully.",
        "role_id": role.id
    })


@csrf_exempt
@require_post
def edit_role(request):
    """
    POST Request:
    {
        "id": 1,
        "role_name": "Field Level Surveyor Updated",
        "role_code": "FIELD_SURVEYOR_UPD",
        "description": "Updated description",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit Role =================================')
    payload = request.data
    logger.info(f'Received edit role payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    role_id = payload.get('id')
    role = RoleMaster.objects.filter(id=role_id).first()
    if not role:
        raise UserNotFoundException(f"Role with ID {role_id} not found.")

    # Store original values for Audit log
    old_data = {
        "role_name": role.role_name,
        "role_code": role.role_code,
        "description": role.description,
        "is_active": role.is_active
    }

    updated = False
    role_name = payload.get('role_name')
    role_code = payload.get('role_code')
    description = payload.get('description')
    is_active = payload.get('is_active')

    # Update role_name if provided
    if role_name is not None:
        role_name = str(role_name).strip()
        if not role_name:
            raise MandatoryInputMissingException("role_name cannot be empty.")
        # Check uniqueness excluding current record
        if RoleMaster.objects.filter(role_name__iexact=role_name).exclude(id=role.id).exists():
            raise UserAlreadyExistException(f"Role Name '{role_name}' already exists.")
        if role.role_name != role_name:
            role.role_name = role_name
            updated = True

    # Update role_code if provided
    if role_code is not None:
        role_code = str(role_code).strip()
        if not role_code:
            raise MandatoryInputMissingException("role_code cannot be empty.")
        # Check uniqueness excluding current record
        if RoleMaster.objects.filter(role_code__iexact=role_code).exclude(id=role.id).exists():
            raise UserAlreadyExistException(f"Role Code '{role_code}' already exists.")
        if role.role_code != role_code:
            role.role_code = role_code
            updated = True

    # Update description if provided
    if description is not None:
        description = str(description).strip()
        if role.description != description:
            role.description = description
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if role.is_active != is_active_val:
            role.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        role.updated_by = user_id
        role.save()

        AuditLog.objects.create(
            table_name='role_master',
            operation='UPDATE',
            ref_id=role.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"Role updated: {role.role_name} ({role.role_code})"
        )

    logger.warning('================================== END - Edit Role =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Role updated successfully."
    })


@csrf_exempt
def list_roles(request):
    """
    GET / POST Request:
    Supports filtering by search query and is_active status.
    """
    logger.warning('================================== START - List Roles =================================')
    payload = request.data
    logger.info(f'Received list roles params: {payload}')

    queryset = RoleMaster.objects.all()

    # Search filter (matches role_name or role_code or description)
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(
            Q(role_name__icontains=search) | Q(role_code__icontains=search) | Q(description__icontains=search)
        )

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    # Order alphabetically by role name
    queryset = queryset.order_by('role_name')

    # Total Count matching filters
    total_count = queryset.count()

    # Pagination parameters
    try:
        page_no = int(payload.get('page_no', 1))
        if page_no < 1:
            page_no = 1
    except (ValueError, TypeError):
        page_no = 1

    try:
        page_size = int(payload.get('page_size', 10))
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    offset = (page_no - 1) * page_size
    limit = page_size

    # Slice queryset for pagination
    queryset = queryset[offset:offset + limit]
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    roles_list = []
    for role in queryset:
        roles_list.append({
            "id": role.id,
            "role_name": role.role_name,
            "role_code": role.role_code,
            "description": role.description,
            "is_active": role.is_active,
            "created_on": role.created_on.strftime('%Y-%m-%d %H:%M:%S') if role.created_on else None,
            "updated_on": role.updated_on.strftime('%Y-%m-%d %H:%M:%S') if role.updated_on else None,
        })

    logger.warning('================================== END - List Roles =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Roles retrieved successfully.",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page_no,
        "page_size": page_size,
        "roles": roles_list
    })


@csrf_exempt
def get_role_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get Role Detail =================================')
    payload = request.data
    logger.info(f'Received get role detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    role_id = payload.get('id')
    role = RoleMaster.objects.filter(id=role_id).first()
    if not role:
        raise UserNotFoundException(f"Role with ID {role_id} not found.")

    logger.warning('================================== END - Get Role Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Role detail retrieved successfully.",
        "role": {
            "id": role.id,
            "role_name": role.role_name,
            "role_code": role.role_code,
            "description": role.description,
            "is_active": role.is_active,
            "created_by": role.created_by,
            "created_on": role.created_on.strftime('%Y-%m-%d %H:%M:%S') if role.created_on else None,
            "updated_by": role.updated_by,
            "updated_on": role.updated_on.strftime('%Y-%m-%d %H:%M:%S') if role.updated_on else None,
        }
    })


@csrf_exempt
@require_post
def add_designation(request):
    """
    POST Request:
    {
        "role_id": 1,
        "designation_name": "Senior Surveyor",
        "designation_code": "SR_SURVEYOR",
        "description": "Senior field surveyor designation"
    }
    """
    logger.warning('================================== START - Add Designation =================================')
    payload = request.data
    logger.info(f'Received add designation payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["role_id", "designation_name", "designation_code"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    role_id = payload.get('role_id')
    designation_name = str(payload.get('designation_name')).strip()
    designation_code = str(payload.get('designation_code')).strip()
    description = payload.get('description')

    if not designation_name or not designation_code:
        raise MandatoryInputMissingException("designation_name and designation_code cannot be empty strings.")

    # Check if Role exists
    role = RoleMaster.objects.filter(id=role_id).first()
    if not role:
        raise UserNotFoundException(f"Role with ID {role_id} not found.")

    # Check for duplicates
    duplicate = DesignationMaster.objects.filter(
        Q(designation_name__iexact=designation_name) | Q(designation_code__iexact=designation_code)
    ).first()

    if duplicate:
        if duplicate.designation_code.lower() == designation_code.lower():
            raise UserAlreadyExistException(f"Designation Code '{designation_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"Designation Name '{designation_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create Designation
    designation = DesignationMaster.objects.create(
        role=role,
        designation_name=designation_name,
        designation_code=designation_code,
        description=description,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='designation_master',
        operation='INSERT',
        ref_id=designation.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"Designation created: {designation.designation_name} ({designation.designation_code}) under Role: {role.role_name}"
    )

    logger.warning('================================== END - Add Designation =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Designation created successfully.",
        "designation_id": designation.id
    })


@csrf_exempt
@require_post
def edit_designation(request):
    """
    POST Request:
    {
        "id": 1,
        "role_id": 2,
        "designation_name": "Senior Surveyor Updated",
        "designation_code": "SR_SURVEYOR_UPD",
        "description": "Updated description",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit Designation =================================')
    payload = request.data
    logger.info(f'Received edit designation payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    designation_id = payload.get('id')
    designation = DesignationMaster.objects.filter(id=designation_id).first()
    if not designation:
        raise UserNotFoundException(f"Designation with ID {designation_id} not found.")

    # Store original values for Audit log
    old_data = {
        "role_id": designation.role.id,
        "designation_name": designation.designation_name,
        "designation_code": designation.designation_code,
        "description": designation.description,
        "is_active": designation.is_active
    }

    updated = False
    role_id = payload.get('role_id')
    designation_name = payload.get('designation_name')
    designation_code = payload.get('designation_code')
    description = payload.get('description')
    is_active = payload.get('is_active')

    # Update role_id if provided
    if role_id is not None:
        role = RoleMaster.objects.filter(id=role_id).first()
        if not role:
            raise UserNotFoundException(f"Role with ID {role_id} not found.")
        if designation.role.id != role.id:
            designation.role = role
            updated = True

    # Update designation_name if provided
    if designation_name is not None:
        designation_name = str(designation_name).strip()
        if not designation_name:
            raise MandatoryInputMissingException("designation_name cannot be empty.")
        # Check uniqueness excluding current record
        if DesignationMaster.objects.filter(designation_name__iexact=designation_name).exclude(id=designation.id).exists():
            raise UserAlreadyExistException(f"Designation Name '{designation_name}' already exists.")
        if designation.designation_name != designation_name:
            designation.designation_name = designation_name
            updated = True

    # Update designation_code if provided
    if designation_code is not None:
        designation_code = str(designation_code).strip()
        if not designation_code:
            raise MandatoryInputMissingException("designation_code cannot be empty.")
        # Check uniqueness excluding current record
        if DesignationMaster.objects.filter(designation_code__iexact=designation_code).exclude(id=designation.id).exists():
            raise UserAlreadyExistException(f"Designation Code '{designation_code}' already exists.")
        if designation.designation_code != designation_code:
            designation.designation_code = designation_code
            updated = True

    # Update description if provided
    if description is not None:
        description = str(description).strip()
        if designation.description != description:
            designation.description = description
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if designation.is_active != is_active_val:
            designation.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        designation.updated_by = user_id
        designation.save()

        AuditLog.objects.create(
            table_name='designation_master',
            operation='UPDATE',
            ref_id=designation.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"Designation updated: {designation.designation_name} ({designation.designation_code})"
        )

    logger.warning('================================== END - Edit Designation =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Designation updated successfully."
    })


@csrf_exempt
def list_designations(request):
    """
    GET / POST Request:
    Supports filtering by role_id, search query, and is_active status.
    """
    logger.warning('================================== START - List Designations =================================')
    payload = request.data
    logger.info(f'Received list designations params: {payload}')

    # Fetch designations, prefetching role model
    queryset = DesignationMaster.objects.select_related('role').all()

    # Filter by role_id
    role_id = payload.get('role_id')
    if role_id is not None:
        queryset = queryset.filter(role_id=role_id)

    # Search filter (matches name, code or description)
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(
            Q(designation_name__icontains=search) | Q(designation_code__icontains=search) | Q(description__icontains=search)
        )

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    # Order alphabetically by designation name
    queryset = queryset.order_by('designation_name')

    # Total Count matching filters
    total_count = queryset.count()

    # Pagination parameters
    try:
        page_no = int(payload.get('page_no', 1))
        if page_no < 1:
            page_no = 1
    except (ValueError, TypeError):
        page_no = 1

    try:
        page_size = int(payload.get('page_size', 10))
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    offset = (page_no - 1) * page_size
    limit = page_size

    # Slice queryset for pagination
    queryset = queryset[offset:offset + limit]
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    designations_list = []
    for designation in queryset:
        designations_list.append({
            "id": designation.id,
            "role_id": designation.role.id,
            "role_name": designation.role.role_name,
            "designation_name": designation.designation_name,
            "designation_code": designation.designation_code,
            "description": designation.description,
            "is_active": designation.is_active,
            "created_on": designation.created_on.strftime('%Y-%m-%d %H:%M:%S') if designation.created_on else None,
            "updated_on": designation.updated_on.strftime('%Y-%m-%d %H:%M:%S') if designation.updated_on else None,
        })

    logger.warning('================================== END - List Designations =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Designations retrieved successfully.",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page_no,
        "page_size": page_size,
        "designations": designations_list
    })


@csrf_exempt
def get_designation_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get Designation Detail =================================')
    payload = request.data
    logger.info(f'Received get designation detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    designation_id = payload.get('id')
    designation = DesignationMaster.objects.select_related('role').filter(id=designation_id).first()
    if not designation:
        raise UserNotFoundException(f"Designation with ID {designation_id} not found.")

    logger.warning('================================== END - Get Designation Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Designation detail retrieved successfully.",
        "designation": {
            "id": designation.id,
            "role_id": designation.role.id,
            "role_name": designation.role.role_name,
            "designation_name": designation.designation_name,
            "designation_code": designation.designation_code,
            "description": designation.description,
            "is_active": designation.is_active,
            "created_by": designation.created_by,
            "created_on": designation.created_on.strftime('%Y-%m-%d %H:%M:%S') if designation.created_on else None,
            "updated_by": designation.updated_by,
            "updated_on": designation.updated_on.strftime('%Y-%m-%d %H:%M:%S') if designation.updated_on else None,
        }
    })

# ==============================================================================
# CONDUCTOR MASTER VIEWS
# ==============================================================================

@csrf_exempt
@require_post
def add_conductor(request):
    """
    POST Request:
    {
        "conductor_name": "AAC Conductor",
        "conductor_code": "AAC_COND",
        "description": "All Aluminum Conductor"
    }
    """
    logger.warning('================================== START - Add Conductor =================================')
    payload = request.data
    logger.info(f'Received add conductor payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["conductor_name", "conductor_code"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    conductor_name = str(payload.get('conductor_name')).strip()
    conductor_code = str(payload.get('conductor_code')).strip()
    description = payload.get('description')

    if not conductor_name or not conductor_code:
        raise MandatoryInputMissingException("conductor_name and conductor_code cannot be empty strings.")

    # Check for duplicates
    duplicate = ConductorMaster.objects.filter(
        Q(conductor_name__iexact=conductor_name) | Q(conductor_code__iexact=conductor_code)
    ).first()

    if duplicate:
        if duplicate.conductor_code.lower() == conductor_code.lower():
            raise UserAlreadyExistException(f"Conductor Code '{conductor_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"Conductor Name '{conductor_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create Conductor
    conductor = ConductorMaster.objects.create(
        conductor_name=conductor_name,
        conductor_code=conductor_code,
        description=description,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='conductor_master',
        operation='INSERT',
        ref_id=conductor.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"Conductor created: {conductor.conductor_name} ({conductor.conductor_code})"
    )

    logger.warning('================================== END - Add Conductor =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Conductor created successfully.",
        "conductor_id": conductor.id
    })


@csrf_exempt
@require_post
def edit_conductor(request):
    """
    POST Request:
    {
        "id": 1,
        "conductor_name": "AAC Conductor Updated",
        "conductor_code": "AAC_COND_UPD",
        "description": "Updated description",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit Conductor =================================')
    payload = request.data
    logger.info(f'Received edit conductor payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    conductor_id = payload.get('id')
    conductor = ConductorMaster.objects.filter(id=conductor_id).first()
    if not conductor:
        raise UserNotFoundException(f"Conductor with ID {conductor_id} not found.")

    # Store original values for Audit log
    old_data = {
        "conductor_name": conductor.conductor_name,
        "conductor_code": conductor.conductor_code,
        "description": conductor.description,
        "is_active": conductor.is_active
    }

    updated = False
    conductor_name = payload.get('conductor_name')
    conductor_code = payload.get('conductor_code')
    description = payload.get('description')
    is_active = payload.get('is_active')

    # Update conductor_name if provided
    if conductor_name is not None:
        conductor_name = str(conductor_name).strip()
        if not conductor_name:
            raise MandatoryInputMissingException("conductor_name cannot be empty.")
        if ConductorMaster.objects.filter(conductor_name__iexact=conductor_name).exclude(id=conductor.id).exists():
            raise UserAlreadyExistException(f"Conductor Name '{conductor_name}' already exists.")
        if conductor.conductor_name != conductor_name:
            conductor.conductor_name = conductor_name
            updated = True

    # Update conductor_code if provided
    if conductor_code is not None:
        conductor_code = str(conductor_code).strip()
        if not conductor_code:
            raise MandatoryInputMissingException("conductor_code cannot be empty.")
        if ConductorMaster.objects.filter(conductor_code__iexact=conductor_code).exclude(id=conductor.id).exists():
            raise UserAlreadyExistException(f"Conductor Code '{conductor_code}' already exists.")
        if conductor.conductor_code != conductor_code:
            conductor.conductor_code = conductor_code
            updated = True

    # Update description if provided
    if description is not None:
        description = str(description).strip()
        if conductor.description != description:
            conductor.description = description
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if conductor.is_active != is_active_val:
            conductor.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        conductor.updated_by = user_id
        conductor.save()

        AuditLog.objects.create(
            table_name='conductor_master',
            operation='UPDATE',
            ref_id=conductor.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"Conductor updated: {conductor.conductor_name} ({conductor.conductor_code})"
        )

    logger.warning('================================== END - Edit Conductor =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Conductor updated successfully."
    })


@csrf_exempt
def list_conductors(request):
    """
    GET / POST Request:
    Supports filtering by search query and is_active status.
    """
    logger.warning('================================== START - List Conductors =================================')
    payload = request.data
    logger.info(f'Received list conductors params: {payload}')

    queryset = ConductorMaster.objects.all()

    # Search filter
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(
            Q(conductor_name__icontains=search) | Q(conductor_code__icontains=search) | Q(description__icontains=search)
        )

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    queryset = queryset.order_by('conductor_name')
    total_count = queryset.count()

    try:
        page_no = int(payload.get('page_no', 1))
        if page_no < 1:
            page_no = 1
    except (ValueError, TypeError):
        page_no = 1

    try:
        page_size = int(payload.get('page_size', 10))
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    offset = (page_no - 1) * page_size
    limit = page_size

    queryset = queryset[offset:offset + limit]
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    conductors_list = []
    for conductor in queryset:
        conductors_list.append({
            "id": conductor.id,
            "conductor_name": conductor.conductor_name,
            "conductor_code": conductor.conductor_code,
            "description": conductor.description,
            "is_active": conductor.is_active,
            "created_on": conductor.created_on.strftime('%Y-%m-%d %H:%M:%S') if conductor.created_on else None,
            "updated_on": conductor.updated_on.strftime('%Y-%m-%d %H:%M:%S') if conductor.updated_on else None,
        })

    logger.warning('================================== END - List Conductors =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Conductors retrieved successfully.",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page_no,
        "page_size": page_size,
        "conductors": conductors_list
    })


@csrf_exempt
def get_conductor_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get Conductor Detail =================================')
    payload = request.data
    logger.info(f'Received get conductor detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    conductor_id = payload.get('id')
    conductor = ConductorMaster.objects.filter(id=conductor_id).first()
    if not conductor:
        raise UserNotFoundException(f"Conductor with ID {conductor_id} not found.")

    logger.warning('================================== END - Get Conductor Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Conductor detail retrieved successfully.",
        "conductor": {
            "id": conductor.id,
            "conductor_name": conductor.conductor_name,
            "conductor_code": conductor.conductor_code,
            "description": conductor.description,
            "is_active": conductor.is_active,
            "created_by": conductor.created_by,
            "created_on": conductor.created_on.strftime('%Y-%m-%d %H:%M:%S') if conductor.created_on else None,
            "updated_by": conductor.updated_by,
            "updated_on": conductor.updated_on.strftime('%Y-%m-%d %H:%M:%S') if conductor.updated_on else None,
        }
    })


@csrf_exempt
@require_post
def delete_conductor(request):
    """
    POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Delete Conductor =================================')
    payload = request.data
    logger.info(f'Received delete conductor payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    conductor_id = payload.get('id')
    conductor = ConductorMaster.objects.filter(id=conductor_id).first()
    if not conductor:
        raise UserNotFoundException(f"Conductor with ID {conductor_id} not found.")

    # Store original values for Audit log
    old_data = {
        "conductor_name": conductor.conductor_name,
        "conductor_code": conductor.conductor_code,
        "description": conductor.description,
        "is_active": conductor.is_active
    }

    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    conductor.delete()

    AuditLog.objects.create(
        table_name='conductor_master',
        operation='DELETE',
        ref_id=conductor_id,
        old_data=old_data,
        updated_by=user_id,
        remarks=f"Conductor deleted: {old_data['conductor_name']} ({old_data['conductor_code']})"
    )

    logger.warning('================================== END - Delete Conductor =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Conductor deleted successfully."
    })


# ==============================================================================
# POLE MASTER VIEWS
# ==============================================================================

@csrf_exempt
@require_post
def add_pole(request):
    """
    POST Request:
    {
        "pole_name": "Concrete Pole 9m",
        "pole_code": "POLE_9M",
        "description": "9 meter concrete pole"
    }
    """
    logger.warning('================================== START - Add Pole =================================')
    payload = request.data
    logger.info(f'Received add pole payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["pole_name", "pole_code"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    pole_name = str(payload.get('pole_name')).strip()
    pole_code = str(payload.get('pole_code')).strip()
    description = payload.get('description')

    if not pole_name or not pole_code:
        raise MandatoryInputMissingException("pole_name and pole_code cannot be empty strings.")

    # Check for duplicates
    duplicate = PoleMaster.objects.filter(
        Q(pole_name__iexact=pole_name) | Q(pole_code__iexact=pole_code)
    ).first()

    if duplicate:
        if duplicate.pole_code.lower() == pole_code.lower():
            raise UserAlreadyExistException(f"Pole Code '{pole_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"Pole Name '{pole_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create Pole
    pole = PoleMaster.objects.create(
        pole_name=pole_name,
        pole_code=pole_code,
        description=description,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='pole_master',
        operation='INSERT',
        ref_id=pole.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"Pole created: {pole.pole_name} ({pole.pole_code})"
    )

    logger.warning('================================== END - Add Pole =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Pole created successfully.",
        "pole_id": pole.id
    })


@csrf_exempt
@require_post
def edit_pole(request):
    """
    POST Request:
    {
        "id": 1,
        "pole_name": "Concrete Pole 9m Updated",
        "pole_code": "POLE_9M_UPD",
        "description": "Updated description",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit Pole =================================')
    payload = request.data
    logger.info(f'Received edit pole payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    pole_id = payload.get('id')
    pole = PoleMaster.objects.filter(id=pole_id).first()
    if not pole:
        raise UserNotFoundException(f"Pole with ID {pole_id} not found.")

    # Store original values for Audit log
    old_data = {
        "pole_name": pole.pole_name,
        "pole_code": pole.pole_code,
        "description": pole.description,
        "is_active": pole.is_active
    }

    updated = False
    pole_name = payload.get('pole_name')
    pole_code = payload.get('pole_code')
    description = payload.get('description')
    is_active = payload.get('is_active')

    # Update pole_name if provided
    if pole_name is not None:
        pole_name = str(pole_name).strip()
        if not pole_name:
            raise MandatoryInputMissingException("pole_name cannot be empty.")
        if PoleMaster.objects.filter(pole_name__iexact=pole_name).exclude(id=pole.id).exists():
            raise UserAlreadyExistException(f"Pole Name '{pole_name}' already exists.")
        if pole.pole_name != pole_name:
            pole.pole_name = pole_name
            updated = True

    # Update pole_code if provided
    if pole_code is not None:
        pole_code = str(pole_code).strip()
        if not pole_code:
            raise MandatoryInputMissingException("pole_code cannot be empty.")
        if PoleMaster.objects.filter(pole_code__iexact=pole_code).exclude(id=pole.id).exists():
            raise UserAlreadyExistException(f"Pole Code '{pole_code}' already exists.")
        if pole.pole_code != pole_code:
            pole.pole_code = pole_code
            updated = True

    # Update description if provided
    if description is not None:
        description = str(description).strip()
        if pole.description != description:
            pole.description = description
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if pole.is_active != is_active_val:
            pole.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        pole.updated_by = user_id
        pole.save()

        AuditLog.objects.create(
            table_name='pole_master',
            operation='UPDATE',
            ref_id=pole.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"Pole updated: {pole.pole_name} ({pole.pole_code})"
        )

    logger.warning('================================== END - Edit Pole =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Pole updated successfully."
    })


@csrf_exempt
def list_poles(request):
    """
    GET / POST Request:
    Supports filtering by search query and is_active status.
    """
    logger.warning('================================== START - List Poles =================================')
    payload = request.data
    logger.info(f'Received list poles params: {payload}')

    queryset = PoleMaster.objects.all()

    # Search filter
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(
            Q(pole_name__icontains=search) | Q(pole_code__icontains=search) | Q(description__icontains=search)
        )

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    queryset = queryset.order_by('pole_name')
    total_count = queryset.count()

    try:
        page_no = int(payload.get('page_no', 1))
        if page_no < 1:
            page_no = 1
    except (ValueError, TypeError):
        page_no = 1

    try:
        page_size = int(payload.get('page_size', 10))
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    offset = (page_no - 1) * page_size
    limit = page_size

    queryset = queryset[offset:offset + limit]
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    poles_list = []
    for pole in queryset:
        poles_list.append({
            "id": pole.id,
            "pole_name": pole.pole_name,
            "pole_code": pole.pole_code,
            "description": pole.description,
            "is_active": pole.is_active,
            "created_on": pole.created_on.strftime('%Y-%m-%d %H:%M:%S') if pole.created_on else None,
            "updated_on": pole.updated_on.strftime('%Y-%m-%d %H:%M:%S') if pole.updated_on else None,
        })

    logger.warning('================================== END - List Poles =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Poles retrieved successfully.",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page_no,
        "page_size": page_size,
        "poles": poles_list
    })


@csrf_exempt
def get_pole_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get Pole Detail =================================')
    payload = request.data
    logger.info(f'Received get pole detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    pole_id = payload.get('id')
    pole = PoleMaster.objects.filter(id=pole_id).first()
    if not pole:
        raise UserNotFoundException(f"Pole with ID {pole_id} not found.")

    logger.warning('================================== END - Get Pole Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Pole detail retrieved successfully.",
        "pole": {
            "id": pole.id,
            "pole_name": pole.pole_name,
            "pole_code": pole.pole_code,
            "description": pole.description,
            "is_active": pole.is_active,
            "created_by": pole.created_by,
            "created_on": pole.created_on.strftime('%Y-%m-%d %H:%M:%S') if pole.created_on else None,
            "updated_by": pole.updated_by,
            "updated_on": pole.updated_on.strftime('%Y-%m-%d %H:%M:%S') if pole.updated_on else None,
        }
    })


@csrf_exempt
@require_post
def delete_pole(request):
    """
    POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Delete Pole =================================')
    payload = request.data
    logger.info(f'Received delete pole payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    pole_id = payload.get('id')
    pole = PoleMaster.objects.filter(id=pole_id).first()
    if not pole:
        raise UserNotFoundException(f"Pole with ID {pole_id} not found.")

    # Store original values for Audit log
    old_data = {
        "pole_name": pole.pole_name,
        "pole_code": pole.pole_code,
        "description": pole.description,
        "is_active": pole.is_active
    }

    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    pole.delete()

    AuditLog.objects.create(
        table_name='pole_master',
        operation='DELETE',
        ref_id=pole_id,
        old_data=old_data,
        updated_by=user_id,
        remarks=f"Pole deleted: {old_data['pole_name']} ({old_data['pole_code']})"
    )

    logger.warning('================================== END - Delete Pole =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Pole deleted successfully."
    })


# ==============================================================================
# TRANSFORMER MASTER VIEWS
# ==============================================================================

@csrf_exempt
@require_post
def add_transformer(request):
    """
    POST Request:
    {
        "transformer_name": "100 KVA Transformer",
        "transformer_code": "TR_100KVA",
        "description": "100 KVA distribution transformer"
    }
    """
    logger.warning('================================== START - Add Transformer =================================')
    payload = request.data
    logger.info(f'Received add transformer payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["transformer_name", "transformer_code"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    transformer_name = str(payload.get('transformer_name')).strip()
    transformer_code = str(payload.get('transformer_code')).strip()
    description = payload.get('description')

    if not transformer_name or not transformer_code:
        raise MandatoryInputMissingException("transformer_name and transformer_code cannot be empty strings.")

    # Check for duplicates
    duplicate = TransformerMaster.objects.filter(
        Q(transformer_name__iexact=transformer_name) | Q(transformer_code__iexact=transformer_code)
    ).first()

    if duplicate:
        if duplicate.transformer_code.lower() == transformer_code.lower():
            raise UserAlreadyExistException(f"Transformer Code '{transformer_code}' already exists.")
        else:
            raise UserAlreadyExistException(f"Transformer Name '{transformer_name}' already exists.")

    # Fetch user ID from authenticated token
    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    # Create Transformer
    transformer = TransformerMaster.objects.create(
        transformer_name=transformer_name,
        transformer_code=transformer_code,
        description=description,
        created_by=user_id,
        updated_by=user_id
    )

    # Create Audit Log
    AuditLog.objects.create(
        table_name='transformer_master',
        operation='INSERT',
        ref_id=transformer.id,
        old_data=None,
        updated_by=user_id,
        remarks=f"Transformer created: {transformer.transformer_name} ({transformer.transformer_code})"
    )

    logger.warning('================================== END - Add Transformer =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Transformer created successfully.",
        "transformer_id": transformer.id
    })


@csrf_exempt
@require_post
def edit_transformer(request):
    """
    POST Request:
    {
        "id": 1,
        "transformer_name": "100 KVA Transformer Updated",
        "transformer_code": "TR_100KVA_UPD",
        "description": "Updated description",
        "is_active": true
    }
    """
    logger.warning('================================== START - Edit Transformer =================================')
    payload = request.data
    logger.info(f'Received edit transformer payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    transformer_id = payload.get('id')
    transformer = TransformerMaster.objects.filter(id=transformer_id).first()
    if not transformer:
        raise UserNotFoundException(f"Transformer with ID {transformer_id} not found.")

    # Store original values for Audit log
    old_data = {
        "transformer_name": transformer.transformer_name,
        "transformer_code": transformer.transformer_code,
        "description": transformer.description,
        "is_active": transformer.is_active
    }

    updated = False
    transformer_name = payload.get('transformer_name')
    transformer_code = payload.get('transformer_code')
    description = payload.get('description')
    is_active = payload.get('is_active')

    # Update transformer_name if provided
    if transformer_name is not None:
        transformer_name = str(transformer_name).strip()
        if not transformer_name:
            raise MandatoryInputMissingException("transformer_name cannot be empty.")
        if TransformerMaster.objects.filter(transformer_name__iexact=transformer_name).exclude(id=transformer.id).exists():
            raise UserAlreadyExistException(f"Transformer Name '{transformer_name}' already exists.")
        if transformer.transformer_name != transformer_name:
            transformer.transformer_name = transformer_name
            updated = True

    # Update transformer_code if provided
    if transformer_code is not None:
        transformer_code = str(transformer_code).strip()
        if not transformer_code:
            raise MandatoryInputMissingException("transformer_code cannot be empty.")
        if TransformerMaster.objects.filter(transformer_code__iexact=transformer_code).exclude(id=transformer.id).exists():
            raise UserAlreadyExistException(f"Transformer Code '{transformer_code}' already exists.")
        if transformer.transformer_code != transformer_code:
            transformer.transformer_code = transformer_code
            updated = True

    # Update description if provided
    if description is not None:
        description = str(description).strip()
        if transformer.description != description:
            transformer.description = description
            updated = True

    # Update is_active if provided
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes']
        else:
            is_active_val = bool(is_active)
        if transformer.is_active != is_active_val:
            transformer.is_active = is_active_val
            updated = True

    # Save changes and log audit trail if updates occurred
    if updated:
        user_id = None
        if hasattr(request, 'token_details') and request.token_details:
            user_id = request.token_details.get('user_id')

        transformer.updated_by = user_id
        transformer.save()

        AuditLog.objects.create(
            table_name='transformer_master',
            operation='UPDATE',
            ref_id=transformer.id,
            old_data=old_data,
            updated_by=user_id,
            remarks=f"Transformer updated: {transformer.transformer_name} ({transformer.transformer_code})"
        )

    logger.warning('================================== END - Edit Transformer =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Transformer updated successfully."
    })


@csrf_exempt
def list_transformers(request):
    """
    GET / POST Request:
    Supports filtering by search query and is_active status.
    """
    logger.warning('================================== START - List Transformers =================================')
    payload = request.data
    logger.info(f'Received list transformers params: {payload}')

    queryset = TransformerMaster.objects.all()

    # Search filter
    search = payload.get('search')
    if search:
        search = str(search).strip()
        queryset = queryset.filter(
            Q(transformer_name__icontains=search) | Q(transformer_code__icontains=search) | Q(description__icontains=search)
        )

    # Active status filter
    is_active = payload.get('is_active')
    if is_active is not None:
        if isinstance(is_active, str):
            is_active_val = is_active.lower() in ['true', '1', 'yes', 'active']
        else:
            is_active_val = bool(is_active)
        queryset = queryset.filter(is_active=is_active_val)

    queryset = queryset.order_by('transformer_name')
    total_count = queryset.count()

    try:
        page_no = int(payload.get('page_no', 1))
        if page_no < 1:
            page_no = 1
    except (ValueError, TypeError):
        page_no = 1

    try:
        page_size = int(payload.get('page_size', 10))
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    offset = (page_no - 1) * page_size
    limit = page_size

    queryset = queryset[offset:offset + limit]
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    transformers_list = []
    for transformer in queryset:
        transformers_list.append({
            "id": transformer.id,
            "transformer_name": transformer.transformer_name,
            "transformer_code": transformer.transformer_code,
            "description": transformer.description,
            "is_active": transformer.is_active,
            "created_on": transformer.created_on.strftime('%Y-%m-%d %H:%M:%S') if transformer.created_on else None,
            "updated_on": transformer.updated_on.strftime('%Y-%m-%d %H:%M:%S') if transformer.updated_on else None,
        })

    logger.warning('================================== END - List Transformers =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Transformers retrieved successfully.",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page_no,
        "page_size": page_size,
        "transformers": transformers_list
    })


@csrf_exempt
def get_transformer_detail(request):
    """
    GET / POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Get Transformer Detail =================================')
    payload = request.data
    logger.info(f'Received get transformer detail params: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    transformer_id = payload.get('id')
    transformer = TransformerMaster.objects.filter(id=transformer_id).first()
    if not transformer:
        raise UserNotFoundException(f"Transformer with ID {transformer_id} not found.")

    logger.warning('================================== END - Get Transformer Detail =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Transformer detail retrieved successfully.",
        "transformer": {
            "id": transformer.id,
            "transformer_name": transformer.transformer_name,
            "transformer_code": transformer.transformer_code,
            "description": transformer.description,
            "is_active": transformer.is_active,
            "created_by": transformer.created_by,
            "created_on": transformer.created_on.strftime('%Y-%m-%d %H:%M:%S') if transformer.created_on else None,
            "updated_by": transformer.updated_by,
            "updated_on": transformer.updated_on.strftime('%Y-%m-%d %H:%M:%S') if transformer.updated_on else None,
        }
    })


@csrf_exempt
@require_post
def delete_transformer(request):
    """
    POST Request:
    {
        "id": 1
    }
    """
    logger.warning('================================== START - Delete Transformer =================================')
    payload = request.data
    logger.info(f'Received delete transformer payload: {payload}')

    # Validate Mandatory Inputs
    required_fields = ["id"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f"Mandatory Required Fields: {required_fields}")

    transformer_id = payload.get('id')
    transformer = TransformerMaster.objects.filter(id=transformer_id).first()
    if not transformer:
        raise UserNotFoundException(f"Transformer with ID {transformer_id} not found.")

    # Store original values for Audit log
    old_data = {
        "transformer_name": transformer.transformer_name,
        "transformer_code": transformer.transformer_code,
        "description": transformer.description,
        "is_active": transformer.is_active
    }

    user_id = None
    if hasattr(request, 'token_details') and request.token_details:
        user_id = request.token_details.get('user_id')

    transformer.delete()

    AuditLog.objects.create(
        table_name='transformer_master',
        operation='DELETE',
        ref_id=transformer_id,
        old_data=old_data,
        updated_by=user_id,
        remarks=f"Transformer deleted: {old_data['transformer_name']} ({old_data['transformer_code']})"
    )

    logger.warning('================================== END - Delete Transformer =================================')
    return JsonResponse({
        "Code": "SUCCESS001",
        "Message": "Transformer deleted successfully."
    })
