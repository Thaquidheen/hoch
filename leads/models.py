import uuid
from django.db import models
from customers.models import Customer

class Pipeline(models.Model):
    pipeline_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID as primary key
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="pipeline_details")
    site_plan = models.BooleanField(default=False)  # True if site plan is completed
    site_photos = models.BooleanField(default=False)  # True if site photos are uploaded
    requirements_checklist = models.BooleanField(default=False)  # True if requirements are fulfilled
    pdf_upload = models.FileField(upload_to='pipelines/pdfs/', null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pipeline for {self.customer.name}"

