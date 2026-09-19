from django.contrib import admin
from django.contrib.auth.hashers import make_password
from constants import PASS_PRE_SALT, PASS_POST_SALT
from common.models import User, LoginActivity, AuditLog, DomainLookup

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'phone', 'email', 'user_type', 'is_active', 'status', 'created_on')
    list_filter = ('is_active', 'user_type')
    search_fields = ('username', 'phone', 'email')

    def save_model(self, request, obj, form, change):
        if obj.password and not (obj.password.startswith('argon2$') or obj.password.startswith('pbkdf2_')):
            salted_password = PASS_PRE_SALT + obj.password + PASS_POST_SALT
            obj.password = make_password(salted_password)
        super().save_model(request, obj, form, change)

@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'm_no', 'user_type', 'active_status', 'login_time', 'logout_time')
    list_filter = ('active_status', 'user_type')
    search_fields = ('m_no',)

@admin.register(DomainLookup)
class DomainLookupAdmin(admin.ModelAdmin):
    list_display = ('domain_id', 'domain_type', 'domain_value', 'domain_code', 'status')
    list_filter = ('domain_type', 'status')
    search_fields = ('domain_type', 'domain_value')
