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
from master_management.models import StateMaster, DistrictMaster

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

