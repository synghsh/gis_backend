from django.contrib import admin
from administration.models import AdminRoleMaster, AdminDesignationMaster, AdminUserDetails

@admin.register(AdminRoleMaster)
class AdminRoleMasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'role_name', 'role_code', 'level', 'is_active')
    search_fields = ('role_name', 'role_code')

@admin.register(AdminDesignationMaster)
class AdminDesignationMasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'designation_name', 'designation_code', 'role', 'hierarchy', 'is_active')
    search_fields = ('designation_name', 'designation_code')

@admin.register(AdminUserDetails)
class AdminUserDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'first_name', 'last_name', 'mob_no', 'email', 'role', 'designation', 'is_active')
    search_fields = ('first_name', 'last_name', 'mob_no', 'email')
