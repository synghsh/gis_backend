from django.urls import path
from master_management.views import (
    add_state, edit_state, list_states, get_state_detail,
    add_district, edit_district, list_districts, get_district_detail
)

urlpatterns = [
    # State Master
    path('state/add/', add_state),
    path('state/edit/', edit_state),
    path('state/list/', list_states),
    path('state/detail/', get_state_detail),

    # District Master
    path('district/add/', add_district),
    path('district/edit/', edit_district),
    path('district/list/', list_districts),
    path('district/detail/', get_district_detail),
]
