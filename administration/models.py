from django.db import models
from common.models import User

class AdminRoleMaster(models.Model):
    id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=100, unique=True)
    role_code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    level = models.SmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'admin_role_master'

    def __str__(self):
        return self.role_name


class AdminDesignationMaster(models.Model):
    id = models.AutoField(primary_key=True)
    designation_name = models.CharField(max_length=150, unique=True)
    designation_code = models.CharField(max_length=50, unique=True)
    role = models.ForeignKey(AdminRoleMaster, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    hierarchy = models.SmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'admin_designation_master'

    def __str__(self):
        return self.designation_name


class AdminUserDetails(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', null=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    mob_no = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(max_length=150, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    pin = models.CharField(max_length=10, null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    designation = models.ForeignKey(AdminDesignationMaster, on_delete=models.SET_NULL, db_column='designation_id', null=True, blank=True)
    role = models.ForeignKey(AdminRoleMaster, on_delete=models.SET_NULL, db_column='role_id', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'admin_user_details'

    def __str__(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        full_name = " ".join([p for p in parts if p])
        return full_name or f"Admin User {self.id}"

