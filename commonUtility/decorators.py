from django.http import HttpResponseBadRequest, JsonResponse
from django.conf import settings
from functools import wraps
from errorcodes import METHOD_NOT_ALLOWED
from commonUtility.utils import get_client_ip

def require_post(func):
    """
    A decorator to ensure that the view only handles POST requests.
    If the request method is not POST, it returns a 400 Bad Request response.
    """
    @wraps(func)
    def wrap(request, *args, **kwargs):
        if request.method != 'POST':
            request.error_code = METHOD_NOT_ALLOWED
            return HttpResponseBadRequest("Invalid Request Method. POST Method Required.")
        return func(request, *args, **kwargs)
    return wrap

def ratelimit_with_ip_whitelist(rate="20/30m", method="POST", key="ip"):
    """
    Applies simple rate limiting with dynamic IP whitelisting based on settings.
    For simplicity in basic setups, we wrap execution without hard blocking unless django-ratelimit is fully loaded.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            client_ip = get_client_ip(request)
            skip_ips = getattr(settings, 'RATE_LIMIT_SKIP_IPS', ['127.0.0.1'])
            if client_ip in skip_ips:
                return view_func(request, *args, **kwargs)
            
            # For standard Django setup we fallback or run django-ratelimit if loaded
            try:
                from django_ratelimit.decorators import ratelimit
                decorated_view = ratelimit(key=key, rate=rate, method=method, block=True)(view_func)
                return decorated_view(request, *args, **kwargs)
            except ImportError:
                # Fallback if django-ratelimit is not fully initialized
                return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
