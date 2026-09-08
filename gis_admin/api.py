from django.urls import path
from administration.views import HealthCheck, userPassLogin, userLogout
from survey_management.views import (
    start_erection_execution,
    list_erection_executions,
    update_erection_execution,
    complete_erection_execution,
    save_erection_node,
    get_erection_pole_details,
)
from common.views import upload_document, get_signed_url, download_document

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
    path('erection/node/save/', save_erection_node),
    path('erection/node/patch/', save_erection_node),
    path('erection/node/update/', save_erection_node),
    path('erection/pole/update/', save_erection_node),
    path('erection/pole/patch/', save_erection_node),
    path('erection/pole/details/', get_erection_pole_details),
    
    # S3 Document Storage APIs
    path('s3/upload/', upload_document),
    path('s3/sign/', get_signed_url),
    path('s3/download/<uuid:doc_id>/', download_document, name='s3-download'),
]

