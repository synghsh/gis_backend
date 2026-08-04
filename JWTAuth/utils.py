import jwt
import logging
from datetime import datetime, timedelta, timezone
from django.db import transaction
from django.conf import settings
from .models import UserToken
from constants import DB_STRF_TIME

logger = logging.getLogger(__name__)

JWT_SECRET = getattr(settings, 'SECRET_KEY', 'default_secret_key')
JWT_ALGO = 'HS256'
TOKEN_VALID_MINUTES = 52560000  # 100 years (effectively never)
REFRESH_WINDOW_MINUTES = 15

def generateToken(user_id, user_type, c_m_no):
    """Generates a new JWT token for a user and registers it in user_token table."""
    try:
        from common.models import User
        from administration.models import AdminUserDetails

        # Fetch basic user details for encoding in payload
        user = User.objects.filter(id=user_id).first()
        username = user.username if user else ""
        phone = user.phone if user else ""
        email = user.email if user else ""
        role_id = user.role_id if user else None
        designation_id = user.designation_id if user else None
        first_name = ""
        last_name = ""

        if user:
            details = AdminUserDetails.objects.filter(user=user).first()
            if details:
                first_name = details.first_name or ""
                last_name = details.last_name or ""
                phone = phone or details.mob_no or ""
                email = email or details.email or ""
                if details.role_id:
                    role_id = details.role_id
                if details.designation_id:
                    designation_id = details.designation_id

        with transaction.atomic():
            now_time = datetime.now(timezone.utc)
            expiry_time = now_time + timedelta(minutes=TOKEN_VALID_MINUTES)
            
            payload = {
                "user_id": user_id,
                "user_type": user_type,
                "c_m_no": c_m_no,
                "username": username,
                "phone": phone,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role_id": role_id,
                "designation_id": designation_id,
                "exp": expiry_time,
                "iat": now_time
            }
            
            token = jwt.encode(payload, key=JWT_SECRET, algorithm=JWT_ALGO)
            
            # Save or update token in database
            UserToken.objects.filter(user_id=user_id, c_m_no=c_m_no, user_type=user_type).delete()
            
            UserToken.objects.create(
                user_id=user_id,
                c_m_no=c_m_no,
                user_type=user_type,
                token=token,
                allow_flag=1,
                expiry_time=expiry_time,
                updated_on=now_time
            )
            
            return token

    except Exception as e:
        logger.exception("Error generating user token")
        return None

def generateRefreshToken(token):
    """Refreshes a token by generating a new token if within the validation window."""
    try:
        payload = jwt.decode(token, key=JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = payload.get('user_id')
        user_type = payload.get('user_type')
        c_m_no = payload.get('c_m_no')
        
        return generateToken(user_id, user_type, c_m_no)
    except Exception as e:
        logger.exception("Error generating refresh token")
        return None
