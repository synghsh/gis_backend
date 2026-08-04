from django.db import models

class User(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    phone = models.CharField(max_length=15, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    user_type = models.IntegerField(null=True, blank=True)
    role_id = models.IntegerField(null=True, blank=True)
    designation_id = models.IntegerField(null=True, blank=True)
    level = models.SmallIntegerField(null=True, blank=True)
    ref_id = models.IntegerField(blank=True, null=True)
    login_flag = models.BooleanField(default=False, null=True)
    is_password_reset = models.BooleanField(default=False, null=True)
    status = models.SmallIntegerField(default=1, null=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    created_by = models.IntegerField(blank=True, null=True)
    updated_by = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "user"


class LoginActivity(models.Model):
    id = models.BigAutoField(primary_key=True)
    m_no = models.CharField(max_length=150, null=True, blank=True)
    user_type = models.IntegerField(null=True, blank=True)
    unique_id = models.CharField(max_length=500, null=True, blank=True)
    login_time = models.DateTimeField(null=True, blank=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    active_status = models.SmallIntegerField(default=1)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'login_activity'


class AuditLog(models.Model):
    audit_id = models.BigAutoField(primary_key=True)
    table_name = models.CharField(max_length=100, null=True)
    operation = models.CharField(max_length=50, null=True)
    ref_id = models.IntegerField(null=True)
    old_data = models.JSONField(null=True, blank=True)
    updated_by = models.BigIntegerField(null=True)
    updated_on = models.DateTimeField(auto_now_add=True)
    remarks = models.CharField(max_length=255, null=True)

    class Meta:
        managed = True
        db_table = 'audit_log'


class DomainLookup(models.Model):
    domain_id = models.AutoField(primary_key=True)
    domain_type = models.CharField(max_length=50, db_index=True)
    domain_value = models.CharField(max_length=500)
    domain_code = models.IntegerField(null=True, blank=True)
    domain_desc = models.TextField(null=True, blank=True)
    domain_data_type = models.CharField(max_length=50, null=True, blank=True)
    status = models.SmallIntegerField(default=1)

    class Meta:
        managed = True
        db_table = "domain_lookup"

    def __str__(self):
        return f"{self.domain_type} - {self.domain_value} ({self.domain_code})"

