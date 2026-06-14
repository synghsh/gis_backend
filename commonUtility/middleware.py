import json
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.db import connections, transaction
from errorcodes import (
    DATA, EXCEPTION, ERROR, TOKEN, STATUS_CODE, CODE, MESSAGE, STATUS_MESSAGE,
    SE001, SE002, INTERNAL_SERVER_ERROR
)
from commonUtility.error_operation import customExceptionBuilder
from commonUtility.utils import get_error_message, get_generic_message
from exception import (
    MandatoryInputMissingException, UnauthorizedAccessException, UserNotFoundException,
    BadRequest, InternalServerError, MethodNotAllowed, InvalidStatusException,
    InvalidUsernameFormatException, InvalidOtpException, UserAlreadyExistException,
    NoOtpDataFoundException, OtpExpiredException, UserInactiveException, InvalidPasswordException
)

logger = logging.getLogger(__name__)

class DataParseMiddleware(MiddlewareMixin):
    """Parses GET, POST, and JSON payloads into request.data"""
    def process_request(self, request):
        data = {}

        # Parse GET query parameters
        if request.method == 'GET':
            data.update(request.GET.dict())

        # Parse POST form body parameters
        if request.method == 'POST':
            data.update(request.POST.dict())

        # Parse raw JSON body parameters
        if request.content_type and 'application/json' in request.content_type:
            try:
                body = json.loads(request.body.decode('utf-8')) if request.body else {}
                if isinstance(body, dict):
                    data.update(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        request.data = data
        return None


class TransactionMiddleware(MiddlewareMixin):
    """Wraps view logic inside database transaction.atomic context"""
    def process_request(self, request):
        request._transaction_middleware_active = True
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(request, '_transaction_middleware_active', False):
            @transaction.atomic
            def atomic_view(*args, **kwargs):
                return view_func(request, *view_args, **view_kwargs)
            request._wrapped_view = atomic_view
        return None
    
    def process_exception(self, request, exception):
        # atomic block will rollback transactions automatically
        return None
    
    def process_response(self, request, response):
        return response


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Catches backend exceptions and maps them to appropriate error codes"""
    def process_exception(self, request, exception):
        request.is_error = True
        request.exception = str(exception)
        request.error_code = 'SE001'
        request.status_code = 500

        exception_map = {
            ValueError: ('BE001', 400),
            KeyError: ('BE001', 400),
            MandatoryInputMissingException: ('BE001', 400),
            BadRequest: ('BE001', 400),
            InvalidUsernameFormatException: ('IN006', 400),
            UnauthorizedAccessException: ('WA001', 401),
            UserInactiveException: ('WA010', 403),
            InvalidOtpException: ('WA006', 422),
            NoOtpDataFoundException: ('WA004', 404),
            OtpExpiredException: ('WA003', 410),
            UserAlreadyExistException: ('WA007', 400),
            UserNotFoundException: ('BE002', 404),
            InvalidPasswordException: ('WA001', 401),
        }

        for exc_type, (code, status) in exception_map.items():
            if isinstance(exception, exc_type):
                request.error_code = code
                request.status_code = status
                break

        logger.exception("Exception caught by ErrorHandlingMiddleware")
        return None


class FinalResponseMiddleware(MiddlewareMixin):
    """Envelopes all JSON responses in the standard enterprise schema structure"""
    def process_response(self, request, response):
        # Initialize defaults safely
        request.is_error = getattr(request, 'is_error', False)
        request.error_code = getattr(request, 'error_code', None)
        request.status_code = getattr(request, 'status_code', response.status_code)
        request.exception = getattr(request, 'exception', None)
        token = getattr(request, 'auth_token', None)

        # Clean up database connections in the pool
        self._close_all_open_connections()

        # Skip formatting for health-checks if desired (or other custom static endpoints)
        # Note: In our setup, we let all JSON api endpoints conform to the envelope.
        if request.path.endswith('/health/'):
            # Allow health check to bypass standard envelope formatting if needed,
            # or map it. Let's map it but let it bypass if the client expects a raw response.
            # We will envelope it for GIS administration, keeping it standardized.
            pass

        # Handle formatting for file downloads or non-JSON responses
        if response.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return response

        final_response = {
            DATA: {},
            EXCEPTION: False,
            ERROR: None,
            TOKEN: token,
            STATUS_CODE: response.status_code
        }

        # Formulate ERROR Envelope
        if request.is_error:
            try:
                error_code = request.error_code or 'SE001'
                error_dict = get_error_message(error_code) or {}
                error_obj = error_dict.get(error_code, {})
                error_message = str(request.exception) if request.exception else error_obj.get('message') or 'System Error'

                ceb = customExceptionBuilder(logger, error_code, error_message)

                final_response[DATA] = {}
                final_response[EXCEPTION] = True
                final_response[ERROR] = ceb.error
                final_response[TOKEN] = token
                final_response[STATUS_CODE] = request.status_code

                return JsonResponse(data=final_response, status=ceb.statusCode)
            except Exception as e:
                logger.exception("Fatal exception inside FinalResponseMiddleware error builder")
                final_response[DATA] = {}
                final_response[EXCEPTION] = True
                final_response[ERROR] = {
                    "System_Errors": [{
                        "Code": "SE999",
                        "Message": "Unhandled middleware exception"
                    }]
                }
                final_response[TOKEN] = token
                final_response[STATUS_CODE] = request.status_code
                return JsonResponse(data=final_response, status=request.status_code)

        # Formulate SUCCESS Envelope (For JsonResponses)
        if isinstance(response, JsonResponse):
            try:
                data = json.loads(response.content.decode())
            except Exception:
                data = {}

            actual_data = data.get("data", data) or {}
            
            success_code = actual_data.get("Code", "SUCCESS001")
            message = actual_data.pop("Message", None) or get_generic_message(success_code) or "Success"
            status_message = actual_data.pop("Status Message", "Success")

            final_response[DATA] = actual_data
            final_response[DATA][CODE] = success_code
            final_response[DATA][MESSAGE] = message
            final_response[DATA][STATUS_MESSAGE] = status_message
            final_response[EXCEPTION] = False
            final_response[ERROR] = None
            final_response[TOKEN] = token
            final_response[STATUS_CODE] = response.status_code

            return JsonResponse(data=final_response, status=response.status_code)

        # Fallback for unexpected non-JSON response types
        if response.status_code >= 400:
            final_response[EXCEPTION] = True
            final_response[ERROR] = {
                "System_Errors": [{
                    "Code": f"SE{response.status_code}",
                    "Message": response.reason_phrase or "HTTP Error"
                }]
            }
            final_response[STATUS_CODE] = response.status_code
            return JsonResponse(data=final_response, status=response.status_code)

        return response

    def _close_all_open_connections(self):
        """Close open database connections to avoid leaks in pool"""
        try:
            for alias in connections.databases:
                conn = connections[alias]
                if conn.connection:
                    conn.close()
                if hasattr(conn, "queries") and conn.queries:
                    conn.queries.clear()
        except Exception as e:
            logger.warning(f"Connection cleanup warning: {e}")
