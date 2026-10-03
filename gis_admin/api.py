from django.urls import path
from administration.views import HealthCheck, userPassLogin, userLogout
from survey_management.views import (
    start_erection_execution,
    list_erection_executions,
    get_erection_detail,
    update_erection_execution,
    complete_erection_execution,
    save_erection_node,
    get_erection_pole_details,
    list_survey_lines,
    get_survey_line_detail,
    save_survey_node,
    get_survey_pole_details,
    update_span_distance,
    get_dashboard_metrics,
)
from common.views import upload_document, get_signed_url, download_document

urls = [
    # Health check
    path('health/', HealthCheck),
    path('dashboard/metrics/', get_dashboard_metrics),
    
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
    path('erection/detail/', get_erection_detail),
    path('erection/span/update/', update_span_distance),
    path('survey/span/update/', update_span_distance),
    
    # Survey APIs
    path('survey/list/', list_survey_lines),
    path('survey/detail/', get_survey_line_detail),
    path('survey/node/save/', save_survey_node),
    path('survey/node/patch/', save_survey_node),
    path('survey/node/update/', save_survey_node),
    path('survey/pole/details/', get_survey_pole_details),
    
    # S3 Document Storage APIs
    path('s3/upload/', upload_document),
    path('s3/sign/', get_signed_url),
    path('s3/download/<uuid:doc_id>/', download_document, name='s3-download'),
]

