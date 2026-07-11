from django.db import models

class StateMaster(models.Model):
    id = models.AutoField(primary_key=True)
    state_code = models.CharField(max_length=50, unique=True, db_index=True)
    state_name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'state_master'

    def __str__(self):
        return f"{self.state_name} ({self.state_code})"
