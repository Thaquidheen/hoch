from django.db import models
import uuid

class Architect(models.Model):
    architect_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Architect Name")
    firm = models.CharField(max_length=255, verbose_name="Firm")
    contact_number = models.CharField(max_length=15, verbose_name="Contact Number")
    principal_architect_name = models.CharField(max_length=255, verbose_name="Principal Architect Name")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
