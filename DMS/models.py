from django.db import models

# Create your models here.
class EventData(models.Model):
    event_type = models.CharField(null=True, blank=True)
    machine_name = models.CharField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    static_data = models.JSONField(null=True, blank=True) # event stretching olduğunda hangi ext olduğunu buraya yazabiliriz

        
class TemporalData(models.Model):
    event = models.ForeignKey(EventData, on_delete=models.DO_NOTHING, null=True)
    dynamic_data = models.JSONField(null=True, blank=True)