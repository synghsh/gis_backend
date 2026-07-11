from django.contrib import admin
from django.urls import path, include
from .api import urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('gis/administration/', include(urls)),
    path('gis/master/', include('master_management.urls')),
]
