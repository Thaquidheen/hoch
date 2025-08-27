from rest_framework import serializers
from .models import WorkflowHistory
from customers.models import Customer
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, date

class WorkflowHistorySerializer(serializers.ModelSerializer):
    customer = serializers.StringRelatedField()
    changed_by = serializers.StringRelatedField()

    class Meta:
        model = WorkflowHistory
        fields = ['workflow_id', 'customer', 'previous_state', 'new_state', 'changed_by', 'timestamp']


class DashboardSummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    leads_count = serializers.IntegerField()
    pipeline_count = serializers.IntegerField()
    design_count = serializers.IntegerField()
    production_count = serializers.IntegerField()
    installation_count = serializers.IntegerField()
    confirmation_count = serializers.IntegerField()
    sign_out_count = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    new_customers_today = serializers.IntegerField()
    state_transitions = serializers.ListField()

class StateDistributionSerializer(serializers.Serializer):
    state = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()

class DailyTrendsSerializer(serializers.Serializer):
    date = serializers.DateField()
    new_leads = serializers.IntegerField()
    state_changes = serializers.IntegerField()
    completed_installations = serializers.IntegerField()

class CustomerProgressSerializer(serializers.Serializer):
    customer_name = serializers.CharField()
    customer_id = serializers.UUIDField()
    current_state = serializers.CharField()
    days_in_current_state = serializers.IntegerField()
    total_days_in_process = serializers.IntegerField()
    state_history = serializers.ListField()

class StateTransitionSerializer(serializers.Serializer):
    from_state = serializers.CharField()
    to_state = serializers.CharField()
    count = serializers.IntegerField()
    avg_days = serializers.FloatField()