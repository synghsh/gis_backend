from django.db import models

class UserToken(models.Model):
    token_id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(null=True, blank=False)
    user_type = models.IntegerField(null=True, blank=False)
    token = models.CharField(max_length=500)
    updated_on = models.DateTimeField(null=True, blank=False)
    expiry_time = models.DateTimeField(null=True, blank=False)
    c_m_no = models.CharField(max_length=15, null=True, blank=False)
    allow_flag = models.IntegerField(default=1, null=True, blank=False)

    class Meta:
        managed = True
        db_table = "user_token"

class FcmToken(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(null=True, blank=False)
    user_type = models.IntegerField(null=True, blank=False)
    token = models.CharField(max_length=500)
    device_type = models.CharField(max_length=20, null=True, blank=False)  # android / ios / web
    created_on = models.DateTimeField(null=True, blank=False)
    created_by = models.BigIntegerField(null=True, blank=False)
    updated_on = models.DateTimeField(null=True, blank=False)
    updated_by = models.BigIntegerField(null=True, blank=False)
    expiry_time = models.DateTimeField(null=True, blank=False)
    c_m_no = models.CharField(max_length=15, null=True, blank=False)
    allow_flag = models.IntegerField(default=1, null=True, blank=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = "fcm_token"
