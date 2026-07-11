from django.urls import path
from master_management.views import (
    add_state, edit_state, list_states, get_state_detail
)

urlpatterns = [
    path('state/add/', add_state),
    path('state/edit/', edit_state),
    path('state/list/', list_states),
    path('state/detail/', get_state_detail),
]
