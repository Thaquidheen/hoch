# quotation_pdf/serializers.py
from rest_framework import serializers
from .models import QuotationPDFCustomization, QuotationPDFTemplate, QuotationPDFHistory

class QuotationPDFTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationPDFTemplate
        fields = ['id', 'name', 'description', 'template_type', 'is_active']

class QuotationPDFCustomizationSerializer(serializers.ModelSerializer):
    template = QuotationPDFTemplateSerializer(read_only=True)
    
    class Meta:
        model = QuotationPDFCustomization
        fields = [
            'id', 'project', 'template', 'include_cabinet_details', 'include_door_details',
            'include_accessories', 'include_accessory_images', 'include_plan_images',
            'include_lighting', 'discount_percentage', 'discount_amount', 'discount_reason',
            'special_instructions', 'installation_notes', 'timeline_notes', 'custom_requirements',
            'selected_plan_images', 'show_item_codes', 'show_dimensions', 'include_warranty_info',
            'include_terms_conditions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class QuotationPDFHistorySerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True)
    
    class Meta:
        model = QuotationPDFHistory
        fields = [
            'id', 'filename', 'file_size', 'total_amount', 'discount_applied',
            'final_amount', 'status', 'generated_at', 'generated_by_name'
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