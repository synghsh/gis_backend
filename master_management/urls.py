from django.urls import path
from master_management.views import (
    add_state, edit_state, list_states, get_state_detail,
    add_district, edit_district, list_districts, get_district_detail,
    add_block, edit_block, list_blocks, get_block_detail,
    add_role, edit_role, list_roles, get_role_detail,
    add_designation, edit_designation, list_designations, get_designation_detail,
    add_conductor, edit_conductor, list_conductors, get_conductor_detail, delete_conductor,
    add_pole, edit_pole, list_poles, get_pole_detail, delete_pole,
    add_transformer, edit_transformer, list_transformers, get_transformer_detail, delete_transformer
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

    # Block Master
    path('block/add/', add_block),
    path('block/edit/', edit_block),
    path('block/list/', list_blocks),
    path('block/detail/', get_block_detail),

    # Role Master
    path('role/add/', add_role),
    path('role/edit/', edit_role),
    path('role/list/', list_roles),
    path('role/detail/', get_role_detail),

    # Designation Master
    path('designation/add/', add_designation),
    path('designation/edit/', edit_designation),
    path('designation/list/', list_designations),
    path('designation/detail/', get_designation_detail),

    # Conductor Master
    path('conductor/add/', add_conductor),
    path('conductor/edit/', edit_conductor),
    path('conductor/list/', list_conductors),
    path('conductor/detail/', get_conductor_detail),
    path('conductor/delete/', delete_conductor),

    # Pole Master
    path('pole/add/', add_pole),
    path('pole/edit/', edit_pole),
    path('pole/list/', list_poles),
    path('pole/detail/', get_pole_detail),
    path('pole/delete/', delete_pole),

    # Transformer Master
    path('transformer/add/', add_transformer),
    path('transformer/edit/', edit_transformer),
    path('transformer/list/', list_transformers),
    path('transformer/detail/', get_transformer_detail),
    path('transformer/delete/', delete_transformer),
]




