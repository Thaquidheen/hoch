from rest_framework import serializers
from .models import Pipeline
from customers.models import Customer
class PipelineSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all()  # This allows updates using `customer_id`
    )
    customer_name = serializers.SerializerMethodField()  # Use SerializerMethodField

    class Meta:
        model = Pipeline
        fields = [
            "pipeline_id",
            "customer",
            "customer_name",  
            "site_plan",
            "site_photos",
            "requirements_checklist",
            "pdf_upload",
            "created_at",
        ]

    def get_customer_name(self, obj):
        # Safely retrieve the related customer's name
        return obj.customer.name if obj.customer else None
