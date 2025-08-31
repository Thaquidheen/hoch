# quotation_pdf/models.py

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from decimal import Decimal
import uuid

class QuotationPDFTemplate(models.Model):
    """PDF Templates for different quotation types"""
    TEMPLATE_TYPE_CHOICES = [
        ('STANDARD', 'Standard Quotation'),
        ('DETAILED', 'Detailed with Images'),
        ('SIMPLE', 'Simple Layout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_type = models.CharField(
        max_length=50, 
        choices=TEMPLATE_TYPE_CHOICES,
        default='DETAILED'
    )
    template_file = models.CharField(
    max_length=255,
    blank=True,
    default='quotation_pdf/detailed_quotation.html',
    help_text="Path to template file relative to templates directory"
    )
    css_file = models.CharField(
        max_length=255,
        blank=True,
        help_text="Path to CSS file for this template"
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['template_type', 'name']
        verbose_name = "PDF Template"
        verbose_name_plural = "PDF Templates"
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default template per type
        if self.is_default:
            QuotationPDFTemplate.objects.filter(
                template_type=self.template_type,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class QuotationPDFHistory(models.Model):
    """Store PDF generation history"""
    STATUS_CHOICES = [
        ('GENERATING', 'Generating'),
        ('GENERATED', 'Generated'),
        ('FAILED', 'Failed'),
        ('ARCHIVED', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.UUIDField(db_index=True, help_text="Reference to Project ID")
    project_name = models.CharField(max_length=200, blank=True)
    customer_name = models.CharField(max_length=200, blank=True)
    
    # File information
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveBigIntegerField(default=0, help_text="File size in bytes")
    
    # Template and customization
    template_type = models.CharField(max_length=50, default='DETAILED')
    template = models.ForeignKey(
        QuotationPDFTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    customizations = models.JSONField(default=dict, blank=True)
    
    # Financial information
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    discount_applied = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    final_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    currency = models.CharField(max_length=3, default='INR')
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='GENERATING')
    generation_time_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # User tracking
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_pdfs'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Email and sharing
    email_sent_count = models.PositiveIntegerField(default=0)
    last_emailed_at = models.DateTimeField(null=True, blank=True)
    share_token = models.CharField(max_length=64, blank=True, unique=True)
    share_expires_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "PDF History"
        verbose_name_plural = "PDF History"
        indexes = [
            models.Index(fields=['project_id', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['customer_name', '-created_at']),
        ]
    
    def __str__(self):
        return f"PDF: {self.filename} ({self.status})"
    
    @property
    def file_size_formatted(self):
        """Return formatted file size"""
        if not self.file_size:
            return 'N/A'
        
        sizes = ['Bytes', 'KB', 'MB', 'GB']
        size = float(self.file_size)
        i = 0
        
        while size >= 1024 and i < len(sizes) - 1:
            size /= 1024
            i += 1
        
        return f"{size:.1f} {sizes[i]}"
    
    @property
    def is_expired(self):
        """Check if share link is expired"""
        from django.utils import timezone
        return self.share_expires_at and self.share_expires_at < timezone.now()


class QuotationPDFCustomization(models.Model):
    """Store PDF customization preferences for projects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.UUIDField(unique=True, db_index=True)
    template = models.ForeignKey(
        QuotationPDFTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Content section toggles
    include_cabinet_details = models.BooleanField(default=True)
    include_door_details = models.BooleanField(default=True)
    include_accessories = models.BooleanField(default=True)
    include_accessory_images = models.BooleanField(default=True)
    include_plan_images = models.BooleanField(default=True)
    include_lighting = models.BooleanField(default=True)
    
    # Display options
    show_item_codes = models.BooleanField(default=True)
    show_dimensions = models.BooleanField(default=True)
    include_warranty_info = models.BooleanField(default=True)
    include_terms_conditions = models.BooleanField(default=True)
    
    # PDF layout options
    header_logo = models.BooleanField(default=True)
    footer_contact = models.BooleanField(default=True)
    page_numbers = models.BooleanField(default=True)
    watermark = models.BooleanField(default=False)
    color_theme = models.CharField(max_length=50, default='default')
    
    # Discount settings
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    discount_reason = models.CharField(max_length=200, blank=True)
    
    # Customer notes
    special_instructions = models.TextField(blank=True)
    installation_notes = models.TextField(blank=True)
    timeline_notes = models.TextField(blank=True)
    custom_requirements = models.TextField(blank=True)
    
    # Selected plan images (JSON field to store image IDs)
    selected_plan_images = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "PDF Customization"
        verbose_name_plural = "PDF Customizations"
    
    def __str__(self):
        return f"Customization for Project {self.project_id}"


class QuotationPDFEmailLog(models.Model):
    """Log PDF email sends"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf_history = models.ForeignKey(
        QuotationPDFHistory,
        on_delete=models.CASCADE,
        related_name='email_logs'
    )
    
    # Email details
    recipient_email = models.EmailField()
    cc_emails = models.JSONField(default=list, blank=True)
    bcc_emails = models.JSONField(default=list, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('BOUNCED', 'Bounced'),
    ], default='PENDING')
    
    error_message = models.TextField(blank=True)
    email_provider_id = models.CharField(max_length=100, blank=True)
    
    # Tracking
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Email tracking (if supported)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = "PDF Email Log"
        verbose_name_plural = "PDF Email Logs"
    
    def __str__(self):
        return f"Email to {self.recipient_email} - {self.status}"


class QuotationPDFShare(models.Model):
    """Manage PDF sharing links"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf_history = models.ForeignKey(
        QuotationPDFHistory,
        on_delete=models.CASCADE,
        related_name='share_links'
    )
    
    # Share settings
    share_token = models.CharField(max_length=64, unique=True, db_index=True)
    password_protected = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=255, blank=True)
    
    # Access controls
    allow_download = models.BooleanField(default=True)
    allow_preview = models.BooleanField(default=True)
    max_downloads = models.PositiveIntegerField(null=True, blank=True)
    max_views = models.PositiveIntegerField(null=True, blank=True)
    
    # Tracking
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    
    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Visitor tracking
    visitor_ips = models.JSONField(default=list, blank=True)
    access_log = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "PDF Share Link"
        verbose_name_plural = "PDF Share Links"
    
    def __str__(self):
        return f"Share link: {self.share_token[:8]}..."
    
    @property
    def is_expired(self):
        """Check if share link is expired"""
        from django.utils import timezone
        return self.expires_at and self.expires_at < timezone.now()
    
    @property
    def is_download_limit_reached(self):
        """Check if download limit is reached"""
        return self.max_downloads and self.download_count >= self.max_downloads
    
    @property
    def is_view_limit_reached(self):
        """Check if view limit is reached"""
        return self.max_views and self.view_count >= self.max_views
    
    def can_access(self):
        """Check if share link can be accessed"""
        return not (
            self.is_expired or 
            self.is_download_limit_reached or 
            self.is_view_limit_reached
        )
    
    def log_access(self, ip_address, action='view'):
        """Log access to share link"""
        from django.utils import timezone
        
        # Update counters
        if action == 'view':
            self.view_count += 1
        elif action == 'download':
            self.download_count += 1
        
        # Track unique visitors
        if ip_address not in self.visitor_ips:
            self.visitor_ips.append(ip_address)
            self.unique_visitors += 1
        
        # Log detailed access
        self.access_log.append({
            'timestamp': timezone.now().isoformat(),
            'ip': ip_address,
            'action': action
        })
        
        self.last_accessed_at = timezone.now()
        self.save()


class QuotationPDFSettings(models.Model):
    """Global PDF generation settings"""
    # Default template settings
    default_template = models.ForeignKey(
        QuotationPDFTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Generation settings
    max_file_size_mb = models.PositiveIntegerField(default=50)
    generation_timeout_seconds = models.PositiveIntegerField(default=120)
    enable_watermark = models.BooleanField(default=False)
    watermark_text = models.CharField(max_length=100, default='DRAFT')
    
    # Email settings
    email_from_address = models.EmailField(blank=True)
    email_from_name = models.CharField(max_length=100, blank=True)
    default_email_subject = models.CharField(
        max_length=200,
        default='Kitchen Quotation - {customer_name}'
    )
    default_email_message = models.TextField(
        default='Please find attached your kitchen quotation.\n\nBest regards,\nSpeisekamer Team'
    )
    
    # Share link settings
    default_share_expiry_hours = models.PositiveIntegerField(default=168)  # 7 days
    enable_password_protection = models.BooleanField(default=True)
    enable_download_tracking = models.BooleanField(default=True)
    
    # Storage settings
    storage_path = models.CharField(max_length=200, default='quotation_pdfs/')
    cleanup_old_files_days = models.PositiveIntegerField(default=90)
    
    # Notification settings
    notify_on_generation = models.BooleanField(default=False)
    notify_on_email = models.BooleanField(default=False)
    notification_email = models.EmailField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "PDF Settings"
        verbose_name_plural = "PDF Settings"
    
    def __str__(self):
        return "PDF Generation Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create settings instance"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'max_file_size_mb': 50,
                'generation_timeout_seconds': 120,
            }
        )
        return settings