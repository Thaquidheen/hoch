from django.db import models
import uuid
from customers.models import Customer
# Create your models here.
class DesignPhase(models.Model):
    designphase_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="design_phases"
    ) 
    plan = models.BooleanField(default=False)
    quotation = models.BooleanField(default=False)
    design = models.BooleanField(default=False)
    submit_to_client = models.BooleanField(default=False)
    client_feedback = models.BooleanField(default=False)
    schedule_client_meeting = models.DateField(null=True, blank=True)  # Date for scheduling client meeting
    design_and_amount_freeze = models.BooleanField(default=False)
    create_client_grp = models.BooleanField(default=False)

    def __str__(self):
        return f"Design Phase for {self.customer.name}"