import uuid
from django.db import models
from customers.models import Customer
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

class WorkflowHistory(models.Model):
    workflow_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID as primary key
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='workflow_histories')
    previous_state = models.CharField(max_length=20, blank=True, null=True)
    new_state = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="workflow_changes",
    null=True,
    blank=True
)
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.customer.name}: {self.previous_state} -> {self.new_state}"
    



class DashboardSummary(models.Model):
    date = models.DateField(unique=True)
    leads_count = models.IntegerField(default=0)
    pipeline_count = models.IntegerField(default=0)
    design_count = models.IntegerField(default=0)
    production_count = models.IntegerField(default=0)
    installation_count = models.IntegerField(default=0)
    total_customers = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dashboard Summary for {self.date}"
