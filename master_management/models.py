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


class DistrictMaster(models.Model):
    id = models.AutoField(primary_key=True)
    state = models.ForeignKey(StateMaster, on_delete=models.PROTECT, related_name='districts', db_column='state_id')
    district_code = models.CharField(max_length=50, unique=True, db_index=True)
    district_name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'district_master'

    def __str__(self):
        return f"{self.district_name} ({self.district_code})"


class BlockMaster(models.Model):
    id = models.AutoField(primary_key=True)
    state = models.ForeignKey(StateMaster, on_delete=models.PROTECT, related_name='blocks', db_column='state_id')
    district = models.ForeignKey(DistrictMaster, on_delete=models.PROTECT, related_name='blocks', db_column='district_id')
    block_code = models.CharField(max_length=50, unique=True, db_index=True)
    block_name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'block_master'

    def __str__(self):
        return f"{self.block_name} ({self.block_code})"


class RoleMaster(models.Model):
    id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=100, unique=True)
    role_code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'role_master'

    def __str__(self):
        return f"{self.role_name} ({self.role_code})"


class DesignationMaster(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.ForeignKey(RoleMaster, on_delete=models.PROTECT, related_name='designations', db_column='role_id')
    designation_name = models.CharField(max_length=150, unique=True)
    designation_code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'designation_master'

    def __str__(self):
        return f"{self.designation_name} ({self.designation_code})"




