from django.db import models
from common.models import User

class SurveyLine(models.Model):
    LINE_TYPES = [
        ('HT_11KV', '11 KV High Tension Line'),
        ('HT_33KV', '33 KV High Tension Line'),
        ('LT_440V', '440 V Low Tension Line'),
    ]

    id = models.BigAutoField(primary_key=True)
    contractor_name = models.CharField(max_length=255, null=True, blank=True)
    line_type = models.CharField(max_length=50, choices=LINE_TYPES)
    surveyor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='survey_lines', null=True)
    
    is_synced = models.BooleanField(default=False)
    status = models.SmallIntegerField(default=1)  # 1 = Active, 2 = Archived
    
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'survey_line'

    def __str__(self):
        return f"{self.contractor_name} - {self.line_type}"


class SurveyNode(models.Model):
    NODE_TYPES = [
        ('POLE', 'Concrete Pole Node'),
        ('DTR', 'Distribution Transformer Node'),
    ]

    id = models.BigAutoField(primary_key=True)
    survey_line = models.ForeignKey(SurveyLine, on_delete=models.CASCADE, related_name='nodes')
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    sequence_number = models.IntegerField()
    name_label = models.CharField(max_length=150)
    
    # Store standard coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # JSON attributes (cablesize, height, tilt, sag, poleType, etc.)
    attributes = models.JSONField(default=dict, blank=True)
    
    # Document upload reference path (photos captured by camera)
    image_path = models.CharField(max_length=500, null=True, blank=True)
    
    parent_label = models.CharField(max_length=150, null=True, blank=True)
    captured_at = models.DateTimeField()
    
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'survey_node'
        ordering = ['sequence_number']

    def __str__(self):
        return f"{self.name_label} ({self.node_type}) - Seq: {self.sequence_number}"
