import logging
from datetime import datetime, timezone
from django.db import connections, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password, make_password

from constants import (
    DB_ALIAS_MASTER, CODE, MESSAGE, ACTIVE, INACTIVE, PASS_PRE_SALT, PASS_POST_SALT
)
from errorcodes import SUCCESSCODE, SUCCESSMESSAGE, SUCCESSCODE3, SUCCESSCODE4
from exception import (
    MandatoryInputMissingException, UserNotFoundException, UserInactiveException,
    InvalidPasswordException, InvalidPasswordFormatException, UnauthorizedAccessException,
    InvalidUsernameFormatException
)
from commonUtility.decorators import ratelimit_with_ip_whitelist, require_post
from commonUtility.utils import (
    mandatoryInputCheck, decode_base64_password, validate_password, validate_phone, validate_email
)
from common.models import User, LoginActivity
from administration.models import AdminUserDetails
from JWTAuth.utils import generateToken
from JWTAuth.models import UserToken

logger = logging.getLogger(__name__)

def HealthCheck(request):
    """Bypasses custom verification check for infrastructure connectivity audits"""
    logger.warning('================================== START - Application Health =================================')
    sysTimeNow = datetime.now().strftime('%d-%m-%Y, %I:%M:%S.%f %p')
    logger.info(f'backendsvc Health Check API - System Local Time : >>>> {sysTimeNow}')

    output = {
        CODE: SUCCESSCODE,
        'Time': sysTimeNow,
        'Condition': "OK",
        'DjangoApp': "GIS Backend Service Health Check API",
        MESSAGE: SUCCESSMESSAGE,
        "DatabaseStatus": "Not Connected"
    }

    try:
        # Check PostgreSQL DB connection activity status
        with connections[DB_ALIAS_MASTER].cursor() as cursor:
            cursor.execute("SELECT current_timestamp;")
            db_time = cursor.fetchone()
        output["DatabaseStatus"] = "Connected"
        output['DatabaseTimestamp'] = db_time[0]
        logger.info("Database connection check successful.")
    except Exception as e:
        logger.exception("Database health check connection failed")
        output["DatabaseStatus"] = f"Failed: {str(e)}"

    logger.warning('=================================== END - Application Health =================================')
    return JsonResponse(output, status=200)


@ratelimit_with_ip_whitelist(rate='20/30m', method='POST')
@csrf_exempt
@require_post
def userPassLogin(request):
    """
    POST Request:
    {
        "username": "9999999900",
        "password": "password_base64_encoded"
    }
    """
    logger.warning('================================== START - Admin User Login With Password =================================')
    current_datetime = datetime.now(timezone.utc)

    payload = request.data
    username = payload.get('username')
    password = payload.get('password')
    
    logger.info(f'Received Login payload - Username: {username}')

    # Validate Mandatory Inputs
    required_fields = ["username", "password"]
    if not mandatoryInputCheck(payload, required_fields):
        raise MandatoryInputMissingException(f'Mandatory Required Fields: {required_fields}')

    # Username Format Validation
    if validate_phone(phone=username):
        if len(username) != 10:
            raise InvalidUsernameFormatException("Phone Number must be exactly 10 digits.")
    elif validate_email(email=username):
        pass
    else:
        if not username.isalnum() and not any(c in username for c in "._-"):
            raise InvalidUsernameFormatException("Invalid Username Format (Must be a 10 digit Phone Number, Email, or Alphanumeric Username).")

    # Fetch User
    user_obj = User.objects.filter(
        Q(username=username) | Q(phone=username) | Q(email=username),
        is_active=True
    ).first()

    if not user_obj:
        raise UserNotFoundException('User is not registered yet.')

    if not user_obj.is_active:
        raise UserInactiveException("User is currently inactive. Contact system administrator.")

    # Decode base64 password from client
    try:
        decoded_password = decode_base64_password(password)
    except Exception:
        raise InvalidPasswordFormatException("Password must be base64 encoded.")

    # Validate password pattern
    if not validate_password(decoded_password):
        raise InvalidPasswordFormatException('Password does not match strength criteria.')

    # Apply Salting matching reference implementation
    salted_password = PASS_PRE_SALT + decoded_password + PASS_POST_SALT

    # Verify Hash
    if not check_password(salted_password, user_obj.password):
        raise InvalidPasswordException('Invalid Password. Please verify and try again.')

    # Fetch AdminUserDetails profile details
    admin_details = AdminUserDetails.objects.filter(user=user_obj).first()

    # Generate Auth Token
    user_type = user_obj.user_type or 1
    token = generateToken(user_obj.id, user_type, user_obj.username)
    if not token:
        raise Exception("Token generation failed")

    with transaction.atomic():
        # Deactivate previous active login sessions
        LoginActivity.objects.filter(
            m_no=user_obj.username,
            user_type=user_type,
            active_status=ACTIVE,
            is_active=True
        ).update(
            active_status=INACTIVE,
            logout_time=current_datetime,
            updated_on=current_datetime
        )

        # Log new login activity session details
        LoginActivity.objects.create(
            m_no=user_obj.username,
            user_type=user_type,
            login_time=current_datetime,
            active_status=ACTIVE,
            created_on=current_datetime,
            is_active=True
        )

        # Update User login flag
        User.objects.filter(id=user_obj.id).update(
            login_flag=True,
            updated_on=current_datetime
        )

    # Attach token to request object for FinalResponseMiddleware injection
    request.auth_token = token

    response_data = {
        "user_details": {
            "id": user_obj.id,
            "username": user_obj.username,
            "phone": user_obj.phone,
            "email": user_obj.email,
            "user_type": user_type,
            "level": user_obj.level,
            "first_name": admin_details.first_name if admin_details else "",
            "middle_name": admin_details.middle_name if admin_details else "",
            "last_name": admin_details.last_name if admin_details else "",
            "address": admin_details.address if admin_details else "",
            "district": admin_details.district if admin_details else "",
            "state": admin_details.state if admin_details else "",
            "pin": admin_details.pin if admin_details else "",
            "joining_date": admin_details.joining_date.strftime('%Y-%m-%d') if admin_details and admin_details.joining_date else None,
            "designation_id": admin_details.designation_id if admin_details else None,
            "role_id": admin_details.role_id if admin_details else None
        },
        "Code": SUCCESSCODE4,
        "Message": "User Login Successful"
    }

    logger.warning('================================== END - Admin User Login with Password =================================')
    return JsonResponse(response_data)



@csrf_exempt
@require_post
def userLogout(request):
    """
    POST Request - Requires authorization token header.
    """
    logger.warning('================================== START - User Logout =================================')
    current_datetime = datetime.now(timezone.utc)
    token_details = getattr(request, 'token_details', None)

    if not token_details or not token_details.get('user_id'):
        raise UnauthorizedAccessException("User is not authenticated.")

    user_id = token_details.get('user_id')
    c_m_no = token_details.get('c_m_no')
    user_type = token_details.get('user_type')

    with transaction.atomic():
        # Invalidate active login activity sessions
        LoginActivity.objects.filter(
            m_no=c_m_no,
            user_type=user_type,
            active_status=ACTIVE
        ).update(
            active_status=INACTIVE,
            logout_time=current_datetime,
            updated_on=current_datetime
        )

        # Remove JWT token record
        UserToken.objects.filter(
            user_id=user_id,
            c_m_no=c_m_no,
            user_type=user_type
        ).delete()

        # Update User login flag status
        User.objects.filter(id=user_id).update(
            login_flag=False,
            updated_on=current_datetime
        )

    response_data = {
        "Code": SUCCESSCODE3,
        "Message": "User Logout Successful"
    }

    logger.warning('================================== END - User Logout =================================')
    return JsonResponse(response_data)
