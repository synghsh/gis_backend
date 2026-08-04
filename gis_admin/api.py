from django.urls import path
from administration.views import HealthCheck, userPassLogin, userLogout
from survey_management.views import (
    start_erection_execution,
    list_erection_executions,
    update_erection_execution,
    complete_erection_execution,
)

urls = [
    # Health check
    path('health/', HealthCheck),
    
    # Auth APIs
    path('admin/login/', userPassLogin),
    path('admin/logout/', userLogout),
    
    # Erection APIs
    path('erection/start/', start_erection_execution),
    path('erection/list/', list_erection_executions),
    path('erection/update/', update_erection_execution),
    path('erection/complete/', complete_erection_execution),
]

