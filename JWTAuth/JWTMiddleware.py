import logging
import jwt
from datetime import datetime, timezone, timedelta
from django.http import JsonResponse
from django.contrib.auth.backends import BaseBackend
from django.db import transaction
from errorcodes import CODE, MESSAGE, TOKEN, FORBIDDEN
from constants import JWT_EXCLUSION_LIST
from .models import UserToken
from .utils import JWT_SECRET, JWT_ALGO, generateRefreshToken, REFRESH_WINDOW_MINUTES

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseBackend):
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        auth_resp = self.auth(request)
        logger.info(f"JWT Auth result: {auth_resp}")
        
        if auth_resp is True:
            return self.get_response(request)
        else:
            code = auth_resp.get(CODE, 403)
            message = auth_resp.get(MESSAGE, "Access Denied")
            resp_data = {MESSAGE: message}
            
            if code == 408:
                # Refresh window hit: include the new token
                logger.info("Access token validation window hit, refreshing token")
                resp_data[TOKEN] = auth_resp.get(TOKEN)
                
            resp = JsonResponse(resp_data, status=code, content_type="application/json")
            return resp

    def auth(self, request):
        path = request.path
        logger.warning(f"Evaluating JWT for path: {path}")

        # Check path exclusions
        if path in JWT_EXCLUSION_LIST:
            request.token_details = {"user_id": None, "user_type": None, "c_m_no": None}
            return True

        token = request.headers.get('Authorization')
        if not token:
            logger.error("Authorization header is missing")
            return {CODE: FORBIDDEN, MESSAGE: "Authorization Token Missing"}

        try:
            # Decode JWT payload
            payload = jwt.decode(token, key=JWT_SECRET, algorithms=[JWT_ALGO])
            logger.info(f"Decoded token payload: {payload}")
            
            user_id = payload.get('user_id')
            user_type = payload.get('user_type')
            c_m_no = payload.get('c_m_no')
            
            request.token_details = {
                "user_id": user_id,
                "user_type": user_type,
                "c_m_no": c_m_no,
                "username": payload.get('username'),
                "phone": payload.get('phone'),
                "email": payload.get('email'),
                "first_name": payload.get('first_name'),
                "last_name": payload.get('last_name'),
                "role_id": payload.get('role_id'),
                "designation_id": payload.get('designation_id')
            }

            exp = payload.get('exp')
            expiry_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            current_time = datetime.now(tz=timezone.utc)
            
            # Fetch token from database to verify persistence/invalidation
            try:
                user_token_obj = UserToken.objects.get(user_id=user_id, c_m_no=c_m_no, user_type=user_type)
            except UserToken.DoesNotExist:
                logger.error("Token record does not exist in database")
                return {CODE: FORBIDDEN, MESSAGE: "Invalid Session (Token not found)"}

            # Check if token matches active database token
            if user_token_obj.token != token:
                logger.error("Token mismatch between header and database record")
                return {CODE: FORBIDDEN, MESSAGE: "Token Mismatch"}

            # Calculate refresh window
            validation_time = expiry_time - timedelta(minutes=REFRESH_WINDOW_MINUTES)
            
            with transaction.atomic():
                if validation_time < current_time < expiry_time:
                    # Within refresh window: generate and return a new token
                    new_token = generateRefreshToken(token)
                    logger.warning("Token in refresh window, returned 408 with new token")
                    return {CODE: 408, MESSAGE: "Refresh Token Generated", TOKEN: new_token}
                
                elif current_time > expiry_time:
                    # Token expired: invalidate record
                    user_token_obj.delete()
                    logger.error("Token is expired, deleted database record")
                    return {CODE: FORBIDDEN, MESSAGE: "Token Expired"}
                
                else:
                    # Token is active and valid
                    return True

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired signature error")
            return {CODE: FORBIDDEN, MESSAGE: "Token Time Out Error"}
        except jwt.DecodeError:
            logger.warning("Token decoding signature error")
            return {CODE: FORBIDDEN, MESSAGE: "Token Invalid Format"}
        except jwt.InvalidTokenError:
            logger.warning("Invalid token error")
            return {CODE: FORBIDDEN, MESSAGE: "Invalid Token"}
        except Exception as e:
            logger.exception("General JWT verification exception occurred")
            return {CODE: FORBIDDEN, MESSAGE: "Token Authentication Error"}
