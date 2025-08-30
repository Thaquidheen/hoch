# Create the quotation_pdf app

# Step 1: Run this command in your project root:
# python manage.py startapp quotation_pdf

# quotation_pdf/models.py
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
import uuid

class QuotationPDFTemplate(models.Model):
    """PDF Templates for different quotation types"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_type = models.CharField(max_length=50, choices=[
        ('STANDARD', 'Standard Quotation'),
        ('DETAILED', 'Detailed with Images'),
        ('SIMPLE', 'Simple Layout'),
    ], default='DETAILED')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"

class QuotationPDFCustomization(models.Model):
    """Store PDF customization preferences for projects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('pricing.Project', on_delete=models.CASCADE, related_name='pdf_customizations')
    template = models.ForeignKey(QuotationPDFTemplate, on_delete=models.PROTECT)
    
    # Section toggles
    include_cabinet_details = models.BooleanField(default=True)
    include_door_details = models.BooleanField(default=True)
    include_accessories = models.BooleanField(default=True)
    include_accessory_images = models.BooleanField(default=True)
    include_plan_images = models.BooleanField(default=True)
    include_lighting = models.BooleanField(default=True)
    
    # Discount settings
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    discount_reason = models.CharField(max_length=200, blank=True)
    
    # Customer notes
    special_instructions = models.TextField(blank=True)
    installation_notes = models.TextField(blank=True)
    timeline_notes = models.TextField(blank=True)
    custom_requirements = models.TextField(blank=True)
    
    # PDF settings
    show_item_codes = models.BooleanField(default=True)
    show_dimensions = models.BooleanField(default=True)
    include_warranty_info = models.BooleanField(default=True)
    include_terms_conditions = models.BooleanField(default=True)
    
    # Selected plan images (JSON field to store image IDs)
    selected_plan_images = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['project', 'template']
    
    def __str__(self):
        return f"PDF Config - {self.project.customer.name} - {self.template.name}"

class QuotationPDFHistory(models.Model):
    """Track generated PDFs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('pricing.Project', on_delete=models.CASCADE, related_name='pdf_history')
    customization = models.ForeignKey(QuotationPDFCustomization, on_delete=models.SET_NULL, null=True)
    
    # File info
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # in bytes
    file_path = models.CharField(max_length=500, blank=True)  # relative path to file
    
    # PDF metadata
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_applied = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    final_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Generation info
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('GENERATED', 'Generated'),
        ('SENT', 'Sent to Customer'),
        ('APPROVED', 'Approved by Customer'),
        ('EXPIRED', 'Expired'),
    ], default='GENERATED')
    
    def __str__(self):
        return f"PDF - {self.project.customer.name} - {self.generated_at.strftime('%Y-%m-%d')}"