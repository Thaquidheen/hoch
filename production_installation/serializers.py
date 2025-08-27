from rest_framework import serializers
from .models import ProductionInstallationPhase

class ProductionInstallationPhaseSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = ProductionInstallationPhase
        fields = [
            "phase_id",
            "customer",
            "customer_name",
            "epd_received",
            "epd_sharing_site_visit",
            "flooring_completed",
            "ceiling_completed",
            "carcass_at_site",
            "countertop_at_site",
            "shutters_at_site",
            "carcass_installed",
            "countertop_installed",
            "shutters_installed",
            "appliances_received_at_site",
            "appliances_installed",
            "light_installed",
            "handover_to_client",
            "client_feedback_photography",
        ]
