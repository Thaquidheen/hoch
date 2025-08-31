from rest_framework import serializers
from .models import (
    QuotationPDFCustomization, 
    QuotationPDFTemplate, 
    QuotationPDFHistory,
    QuotationPDFEmailLog,
    QuotationPDFShare
)

class QuotationPDFTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationPDFTemplate
        fields = ['id', 'name', 'description', 'template_type', 'is_active', 'is_default']
        read_only_fields = ['id']

class QuotationPDFCustomizationSerializer(serializers.ModelSerializer):
    template = QuotationPDFTemplateSerializer(read_only=True)
    template_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = QuotationPDFCustomization
        fields = [
            'id', 'project_id', 'template', 'template_id', 'include_cabinet_details', 
            'include_door_details', 'include_accessories', 'include_accessory_images', 
            'include_plan_images', 'include_lighting', 'show_item_codes', 'show_dimensions', 
            'include_warranty_info', 'include_terms_conditions', 'header_logo', 'footer_contact',
            'page_numbers', 'watermark', 'color_theme', 'discount_percentage', 'discount_amount', 
            'discount_reason', 'special_instructions', 'installation_notes', 'timeline_notes', 
            'custom_requirements', 'selected_plan_images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        template_id = validated_data.pop('template_id', None)
        if template_id:
            try:
                template = QuotationPDFTemplate.objects.get(id=template_id)
                validated_data['template'] = template
            except QuotationPDFTemplate.DoesNotExist:
                pass
        return super().create(validated_data)

    def update(self, instance, validated_data):
        template_id = validated_data.pop('template_id', None)
        if template_id is not None:
            try:
                template = QuotationPDFTemplate.objects.get(id=template_id) if template_id else None
                validated_data['template'] = template
            except QuotationPDFTemplate.DoesNotExist:
                pass
        return super().update(instance, validated_data)

class QuotationPDFHistorySerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True)
    file_size_formatted = serializers.ReadOnlyField()
    
    class Meta:
        model = QuotationPDFHistory
        fields = [
            'id', 'project_id', 'project_name', 'customer_name', 'filename', 
            'file_path', 'file_size', 'file_size_formatted', 'template_type',
            'total_amount', 'discount_applied', 'final_amount', 'currency',
            'status', 'generation_time_seconds', 'error_message',
            'email_sent_count', 'view_count', 'download_count',
            'created_at', 'updated_at', 'generated_by_name'
        ]
        read_only_fields = ['id', 'file_size_formatted', 'created_at', 'updated_at']

class QuotationPDFEmailLogSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.CharField(source='sent_by.username', read_only=True)
    
    class Meta:
        model = QuotationPDFEmailLog
        fields = [
            'id', 'recipient_email', 'cc_emails', 'bcc_emails', 'subject', 
            'message', 'status', 'error_message', 'sent_at', 'sent_by_name',
            'opened_at', 'clicked_at'
        ]
        read_only_fields = ['id', 'sent_at', 'sent_by_name']

class QuotationPDFShareSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    is_expired = serializers.ReadOnlyField()
    can_access = serializers.ReadOnlyField()
    
    class Meta:
        model = QuotationPDFShare
        fields = [
            'id', 'share_token', 'password_protected', 'allow_download', 
            'allow_preview', 'max_downloads', 'max_views', 'view_count', 
            'download_count', 'unique_visitors', 'created_at', 'expires_at', 
            'last_accessed_at', 'created_by_name', 'is_expired', 'can_access'
        ]
        read_only_fields = [
            'id', 'share_token', 'view_count', 'download_count', 'unique_visitors',
            'created_at', 'last_accessed_at', 'created_by_name', 'is_expired', 'can_access'
        ]

# Additional serializers for API responses
class PDFPreviewSummarySerializer(serializers.Serializer):
    """Serializer for PDF preview data summary"""
    cabinet_categories = serializers.IntegerField()
    door_materials = serializers.IntegerField()
    accessory_groups = serializers.IntegerField()
    plan_images = serializers.IntegerField()
    lighting_items = serializers.IntegerField()

class PDFCalculationsSerializer(serializers.Serializer):
    """Serializer for pricing calculations"""
    line_items_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    accessories_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    lighting_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    discount_reason = serializers.CharField(max_length=200, allow_blank=True)
    final_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Formatted strings
    formatted = serializers.DictField(read_only=True)

class PDFProjectInfoSerializer(serializers.Serializer):
    """Serializer for project information in PDF"""
    id = serializers.UUIDField()
    customer_name = serializers.CharField(max_length=200)
    project_type = serializers.CharField(max_length=100)
    quotation_number = serializers.CharField(max_length=100)
    quotation_date = serializers.CharField(max_length=50)
    brand = serializers.CharField(max_length=100, allow_blank=True)
    budget_tier = serializers.CharField(max_length=50)
    kitchen_types = serializers.DictField()
    notes = serializers.CharField(allow_blank=True)

class PDFPreviewResponseSerializer(serializers.Serializer):
    """Complete serializer for PDF preview response"""
    project_info = PDFProjectInfoSerializer()
    calculations = PDFCalculationsSerializer()
    sections_summary = PDFPreviewSummarySerializer()

# Serializer for bulk operations
class BulkPDFGenerationSerializer(serializers.Serializer):
    """Serializer for bulk PDF generation requests"""
    project_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50  # Limit bulk operations
    )
    template_id = serializers.UUIDField(required=False, allow_null=True)
    customizations = serializers.JSONField(required=False, default=dict)

class PDFGenerationRequestSerializer(serializers.Serializer):
    """Serializer for single PDF generation request"""
    project_id = serializers.UUIDField()
    template_id = serializers.UUIDField(required=False, allow_null=True)
    customizations = serializers.JSONField(required=False, default=dict)
    email_recipients = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True
    )
    create_share_link = serializers.BooleanField(default=False)
    share_settings = serializers.JSONField(required=False, default=dict)

class PDFGenerationResponseSerializer(serializers.Serializer):
    """Serializer for PDF generation response"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    pdf_history_id = serializers.UUIDField(required=False, allow_null=True)
    share_link = serializers.CharField(required=False, allow_blank=True)
    download_url = serializers.CharField(required=False, allow_blank=True)
    error_details = serializers.DictField(required=False)

# Nested serializers for detailed responses
class QuotationPDFHistoryDetailSerializer(QuotationPDFHistorySerializer):
    """Extended history serializer with email logs and share links"""
    email_logs = QuotationPDFEmailLogSerializer(many=True, read_only=True)
    share_links = QuotationPDFShareSerializer(many=True, read_only=True)
    template = QuotationPDFTemplateSerializer(read_only=True)
    
    class Meta(QuotationPDFHistorySerializer.Meta):
        fields = QuotationPDFHistorySerializer.Meta.fields + [
            'email_logs', 'share_links', 'template', 'customizations'
        ]