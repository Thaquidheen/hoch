from rest_framework import serializers
from .models import DesignPhase



class DesignPhaseSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_location = serializers.CharField(source="customer.location", read_only=True)

    class Meta:
        model = DesignPhase
        fields = [
            "designphase_id",
            "customer",
            "customer_name",
            "customer_location",
            "plan",
            "quotation",
            "design",
            "submit_to_client",
            "client_feedback",
            "schedule_client_meeting",
            "design_and_amount_freeze",
            "create_client_grp",
        ]