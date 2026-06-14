from django.urls import path
from administration.views import HealthCheck, userPassLogin, userLogout

urls = [
    # Health check
    path('health/', HealthCheck),
    
    # Auth APIs
    path('admin/login/', userPassLogin),
    path('admin/logout/', userLogout),
]
