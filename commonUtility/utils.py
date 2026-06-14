import base64
import logging
import re
from typing import Optional
from errorcodes import SUCCESS_MESSAGES, BE001, BE001MESSAGE
from constants import PHONE_REGEX, EMAIL_REGEX, NAME_REGEX, PASS_REGEX
from exception import MandatoryInputMissingException

logger = logging.getLogger(__name__)

def get_error_message(code):
    """Fetch error message from error code definition."""
    # ASRLM uses database-driven dynamic message mapping stored in cache,
    # we'll use a local fallback dictionary based on errorcodes.py
    import errorcodes
    error_map = {
        'BE001': {'message': errorcodes.BE001MESSAGE},
        'BE002': {'message': errorcodes.BE002MESSAGE},
        'BE003': {'message': errorcodes.BE003MESSAGE},
        'BE007': {'message': errorcodes.BE007MESSAGE},
        'BE008': {'message': errorcodes.BE008MESSAGE},
        'BE014': {'message': errorcodes.BE014MESSAGE},
        'IN006': {'message': errorcodes.IN006MESSAGE},
        'IN002': {'message': errorcodes.IN002MESSAGE},
        'SE001': {'message': errorcodes.SE001MESSAGE},
        'SE002': {'message': errorcodes.SE002MESSAGE},
        'SE003': {'message': errorcodes.SE003MESSAGE},
        'WA001': {'message': errorcodes.WA001MESSAGE},
        'WA003': {'message': errorcodes.WA003MESSAGE},
        'WA004': {'message': errorcodes.WA004MESSAGE},
        'WA006': {'message': errorcodes.WA006MESSAGE},
        'WA007': {'message': errorcodes.WA007MESSAGE},
        'WA010': {'message': errorcodes.WA010MESSAGE},
    }
    return error_map or {}

def get_generic_message(code, default="Operation Completed"):
    if not code:
        return default
    return SUCCESS_MESSAGES.get(code, default)

def mandatoryInputCheck(payload, required_fields):
    if not isinstance(payload, dict):
        return False
    missing = [field for field in required_fields if field not in payload]
    empty_fields = [field for field in required_fields if field in payload and payload.get(field) in [None, "", []]]
    if missing or empty_fields:
        logger.info(f"Missing: {missing}, Empty: {empty_fields}")
        return False
    return True

def get_client_ip(request):
    """Fetch client IP from request headers or remote address."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded.split(',')[0] if x_forwarded else request.META.get("REMOTE_ADDR")

def decode_base64_password(encoded_password: str):
    return base64.b64decode(encoded_password).decode('utf-8')

def validate_phone(phone):
    """Validate a Phone Number"""
    try:
        phone_regex = re.compile(PHONE_REGEX)
        if re.fullmatch(phone_regex, str(phone)):
            return True
        else:
            raise Exception("No Phone Number Matched With Respective Pattern")
    except Exception as e:
        logger.exception(e)
        return False

def validate_email(email):
    """Validate An Email"""
    try:
        email_regex = re.compile(EMAIL_REGEX)
        if re.fullmatch(email_regex, str(email)):
            return True
        return False
    except Exception as e:
        logger.exception(e)
        return False

def validate_name(name):
    """Validate A Name"""
    try:
        name_regex = re.compile(NAME_REGEX)
        if re.fullmatch(name_regex, str(name)):
            return True
        else:
            raise Exception("No Name Matched With Respective Pattern")
    except Exception as e:
        logger.exception(e)
        return False

def validate_password(password):
    """Validate A Password"""
    try:
        password_regex = re.compile(PASS_REGEX)
        if re.fullmatch(password_regex, str(password)):
            return True
        else:
            raise Exception("Entered Password Couldn't Match Respective Pattern")
    except Exception as e:
        logger.exception(e)
        return False

def dictfetchall(cursor):
    """Convert cursor results to list of dicts; return None for columns if no rows."""
    column_names = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    if not rows:  
        return [{col: None for col in column_names}]
    return [dict(zip(column_names, row)) for row in rows]

def dictfetchall2(cursor):
    """Convert cursor results to list of dicts; return empty list if no rows."""
    column_names = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    if not rows: 
        return []
    return [dict(zip(column_names, row)) for row in rows]
