from django.db import models
import uuid
from customers.models import Customer

class ProductionInstallationPhase(models.Model):
    phase_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="production_installation_phases")

    # Fields for each step in the phase
    epd_received = models.BooleanField(default=False)
    epd_sharing_site_visit = models.BooleanField(default=False)
    flooring_completed = models.BooleanField(default=False)
    ceiling_completed = models.BooleanField(default=False)
    carcass_at_site = models.BooleanField(default=False)
    countertop_at_site = models.BooleanField(default=False)
    shutters_at_site = models.BooleanField(default=False)
    carcass_installed = models.BooleanField(default=False)
    countertop_installed = models.BooleanField(default=False)
    shutters_installed = models.BooleanField(default=False)
    appliances_received_at_site = models.BooleanField(default=False)
    appliances_installed = models.BooleanField(default=False)
    light_installed = models.BooleanField(default=False)
    handover_to_client = models.BooleanField(default=False)
    client_feedback_photography = models.BooleanField(default=False)

    def __str__(self):
        return f"Production & Installation Phase for {self.customer.name}"
