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
from master_management.models import StateMaster

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
