from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from catalog.models import Category, Brand,ProductVariant
from customers.models import Customer
import os
import uuid

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class Materials(TimeStamped):
    ROLE_CHOICES = (
        ('CABINET', 'CABINET'), 
        ('DOOR', 'DOOR'), 
        ('TOP', 'TOP'), 
        ('BOTH', 'BOTH')
    )
    name = models.CharField(max_length=120, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='BOTH')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class BudgetTier(models.TextChoices):
    LUXURY = 'LUXURY', 'LUXURY'
    ECONOMY = 'ECONOMY', 'ECONOMY'









# Add missing Accessories model (referenced in ProjectLineItemAccessory)
class Accessories(TimeStamped):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    currency = models.CharField(max_length=3, default='INR')
    
    class Meta:
        verbose_name_plural = "Accessories"
    
    def __str__(self):
        return self.name


class FinishRates(TimeStamped):
    material = models.ForeignKey(Materials, on_delete=models.PROTECT, related_name='cabinet_rates')
    budget_tier = models.CharField(max_length=10, choices=BudgetTier.choices)
    unit_rate = models.DecimalField(max_digits=12, decimal_places=2)  # per SQFT
    currency = models.CharField(max_length=3, default='INR')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    class Meta:
        unique_together = ('material', 'budget_tier', 'effective_from')
    
    def __str__(self):
        return f'{self.material.name} {self.budget_tier} @ {self.unit_rate}'


class DoorFinishRates(TimeStamped):
    material = models.ForeignKey(Materials, on_delete=models.PROTECT, related_name='door_rates')
    unit_rate = models.DecimalField(max_digits=12, decimal_places=2)  # per SQFT
    currency = models.CharField(max_length=3, default='INR')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    class Meta:
        unique_together = ('material', 'effective_from')
    
    def __str__(self):
        return f'{self.material.name} door @ {self.unit_rate}'


class CabinetTypes(TimeStamped):
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        help_text="Category this cabinet type belongs to"
    )
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    # Add default_depth field that seems to be used in frontend
    default_depth = models.PositiveIntegerField(default=600, help_text="Default depth in mm")
    
    class Meta:
        verbose_name_plural = "Cabinet Types"
    
    def __str__(self):
        return self.name


class CabinetTypeBrandCharge(TimeStamped):
    cabinet_type = models.ForeignKey(CabinetTypes, on_delete=models.PROTECT, related_name='brand_charges')
    # You can uncomment this if you want to use Brand FK instead of brand_name
    # brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='cabinet_charges')
    brand_name = models.CharField(max_length=100)  # if not linking to Brand directly
    standard_accessory_charge = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='INR')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    class Meta:
        unique_together = ('cabinet_type', 'brand_name', 'effective_from')
        verbose_name = "Cabinet Type Brand Charge"
        verbose_name_plural = "Cabinet Type Brand Charges"
    
    def __str__(self):
        return f'{self.cabinet_type} - {self.brand_name} - {self.standard_accessory_charge}'


class GeometryRule(TimeStamped):
    cabinet_type = models.ForeignKey(CabinetTypes, on_delete=models.PROTECT, related_name='geometry_rules')
    formula_cabinet_sqft = models.TextField()  # expression/JSON evaluated in service layer
    formula_door_sqft = models.TextField()
    parameters = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f'Geom {self.cabinet_type.name}'


class Project(TimeStamped):
    STATUS = (
        ('DRAFT', 'DRAFT'), 
        ('QUOTED', 'QUOTED'), 
        ('CONFIRMED', 'CONFIRMED'),
        ('IN_PRODUCTION', 'IN_PRODUCTION'), 
        ('DELIVERED', 'DELIVERED'), 
        ('CANCELLED', 'CANCELLED')
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='projects')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT)  # use FK
    budget_tier = models.CharField(max_length=10, choices=BudgetTier.choices)
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    gst_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18'))
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS, default='DRAFT')
    scopes = models.JSONField(default=dict, blank=True)  # e.g. {"open": True, "working": True}
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f'Project {self.id} - {self.customer.name}'


class ProjectLineItem(TimeStamped):
    SCOPE_CHOICES = (
        ('OPEN', 'OPEN'), 
        ('WORKING', 'WORKING')
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='lines')
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='OPEN')
    cabinet_type = models.ForeignKey(CabinetTypes, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1)
    width_mm = models.PositiveIntegerField()
    depth_mm = models.PositiveIntegerField()
    height_mm = models.PositiveIntegerField()
    cabinet_material = models.ForeignKey(
        Materials, 
        on_delete=models.PROTECT, 
        related_name='line_cabinet_material'
    )
    door_material = models.ForeignKey(
        Materials, 
        on_delete=models.PROTECT, 
        related_name='line_door_material'
    )
    
    # Computed fields
    computed_cabinet_sqft = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    computed_door_sqft = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    
    # Pricing fields
    cabinet_unit_rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    door_unit_rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    cabinet_material_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    standard_accessory_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    door_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    top_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    
    line_total_before_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    currency = models.CharField(max_length=3, default='INR')
    remarks = models.TextField(blank=True)
    
    def __str__(self):
        return f'{self.project} - {self.cabinet_type} ({self.qty}x)'

class ProjectLineItemAccessory(TimeStamped):
    """Project accessories using ProductVariants from catalog"""
    line_item = models.ForeignKey(ProjectLineItem, on_delete=models.CASCADE, related_name='extra_accessories')
    product_variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT)  # Now required
    
    qty = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    tax_rate_snapshot = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    installation_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = [('line_item', 'product_variant')]  # Prevent duplicate accessories per line item
        ordering = ['line_item', 'id']
    
    def save(self, *args, **kwargs):
        # Auto-populate pricing from product variant if not set
        if not self.unit_price:
            self.unit_price = self.product_variant.company_price
            self.tax_rate_snapshot = self.product_variant.tax_rate
        
        # Calculate total
        self.total_price = (self.unit_price * self.qty).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
    
    @property
    def accessory_name(self):
        """Display name for the accessory"""
        return f"{self.product_variant.product.name} - {self.product_variant.color_name}"
    
    @property
    def accessory_image(self):
        """Get product image URL"""
        return getattr(self.product_variant, 'image_url', None)
    
    @property
    def material_code(self):
        """Get material code"""
        return self.product_variant.material_code
    
    @property
    def dimensions(self):
        """Get dimensions display"""
        return getattr(self.product_variant, 'dimensions_display', None)
    
    def __str__(self):
        return f'{self.line_item} - {self.accessory_name} ({self.qty}x)'

class ProjectTotals(TimeStamped):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='totals')
    subtotal_cabinets = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    subtotal_doors = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    subtotal_accessories = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    subtotal_tops = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    margin_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    currency = models.CharField(max_length=3, default='INR')
    
    def __str__(self):
        return f'Totals for {self.project}'




def plan_image_upload_path(instance, filename):
    """Generate upload path for plan images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    return f'projects/{instance.image_group.project.id}/plans/{instance.image_group.id}/{filename}'

class ProjectPlanImageGroup(TimeStamped):
    """Groups of images with headings for better organization"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='image_groups')
    title = models.CharField(max_length=200, help_text="Group heading (e.g., 'Floor Plans', '3D Renderings')")
    description = models.TextField(blank=True, help_text="Optional description of this image group")
    sort_order = models.PositiveIntegerField(default=0, help_text="Order for displaying groups")
    
    class Meta:
        ordering = ['sort_order', 'created_at']
        unique_together = [('project', 'title')]  # Prevent duplicate titles per project
    
    def __str__(self):
        return f"{self.project} - {self.title}"
    
    @property
    def image_count(self):
        """Get count of images in this group"""
        return self.images.filter(is_active=True).count()
    
    @property
    def first_image_url(self):
        """Get URL of first image for group thumbnail"""
        first_image = self.images.filter(is_active=True).first()
        return first_image.image.url if first_image else None

class ProjectPlanImage(TimeStamped):
    """Individual images within groups"""
    image_group = models.ForeignKey(
        ProjectPlanImageGroup, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(
        upload_to=plan_image_upload_path,
        help_text="Plan image file (JPG, PNG, PDF supported)"
    )
    caption = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Image caption or description"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for displaying images within group"
    )
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    file_type = models.CharField(max_length=20, blank=True, help_text="File MIME type")
    
    class Meta:
        ordering = ['sort_order', 'created_at']
    
    def save(self, *args, **kwargs):
        # Auto-populate file metadata
        if self.image:
            self.file_size = self.image.size if hasattr(self.image, 'size') else None
            self.file_type = getattr(self.image.file, 'content_type', '')
            
        # Auto-generate caption from filename if not provided
        if not self.caption and self.image:
            filename = os.path.basename(self.image.name)
            self.caption = os.path.splitext(filename)[0].replace('_', ' ').title()
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.image_group.title} - {self.caption or f'Image {self.id}'}"
    
    @property
    def thumbnail_url(self):
        """Get thumbnail URL (implement thumbnail generation if needed)"""
        return self.image.url  # For now, return original image URL
    
    @property
    def file_size_display(self):
        """Human readable file size"""
        if not self.file_size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"


class LightingRules(TimeStamped):
    """Enhanced lighting rules to support different cabinet types and materials"""
    CALC_METHOD_CHOICES = [
        ('PER_WIDTH', 'Per Cabinet Width (mm)'),
        ('PER_LM', 'Per Linear Meter'), 
        ('FLAT_RATE', 'Flat Rate per Cabinet'),
        ('WALL_ONLY', 'Wall Cabinets Only'),
    ]
    
    # Basic Info
    name = models.CharField(max_length=100)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE)
    is_global = models.BooleanField(default=True)
    
    # Material and Type Specificity
    cabinet_material = models.ForeignKey(Materials, on_delete=models.CASCADE)
    cabinet_type = models.ForeignKey(CabinetTypes, null=True, blank=True, on_delete=models.CASCADE, 
                                   help_text="Specific cabinet type (optional - leave blank for all types)")
    budget_tier = models.CharField(max_length=10, choices=BudgetTier.choices)
    calc_method = models.CharField(max_length=20, choices=CALC_METHOD_CHOICES)
    
    # Pricing
    led_strip_rate_per_mm = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('2.0'))
    spot_light_rate_per_cabinet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500'))
    
    # Specifications
    led_specification = models.TextField(blank=True)
    spot_light_specification = models.TextField(blank=True)
    
    # Applicability
    applies_to_wall_cabinets = models.BooleanField(default=True)
    applies_to_base_cabinets = models.BooleanField(default=False)
    
    # Date Management
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='INR')
    
    class Meta:
        unique_together = [
            ('customer', 'cabinet_material', 'cabinet_type', 'budget_tier', 'effective_from'),
        ]
    
    def __str__(self):
        type_name = f" - {self.cabinet_type.name}" if self.cabinet_type else ""
        customer_name = f" ({self.customer.name})" if self.customer else " (Global)"
        return f"{self.cabinet_material.name}{type_name} {self.budget_tier}{customer_name}"


class ProjectLightingConfiguration(TimeStamped):
    """Master lighting configuration for a project"""
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='lighting_config')
    
    # Manual inputs
    work_top_length_mm = models.IntegerField(default=0, help_text="Total work top length for nosing LEDs")
    
    # Project totals (computed from line items)
    total_wall_cabinet_width_mm = models.IntegerField(default=0)
    total_base_cabinet_width_mm = models.IntegerField(default=0) 
    total_wall_cabinet_count = models.IntegerField(default=0)
    
    # Overall totals (computed from lighting items)
    grand_total_lighting_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='INR')
    
    def __str__(self):
        return f"Lighting Config - {self.project}"


class ProjectLightingItem(TimeStamped):
    """Individual lighting item for different materials/types"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='lighting_items')
    lighting_rule = models.ForeignKey(LightingRules, on_delete=models.PROTECT)
    
    # Material and Type Context
    cabinet_material = models.ForeignKey(Materials, on_delete=models.CASCADE)
    cabinet_type = models.ForeignKey(CabinetTypes, null=True, blank=True, on_delete=models.CASCADE)
    
    # Dimensions (specific to this material/type combination)
    wall_cabinet_width_mm = models.IntegerField(default=0)
    base_cabinet_width_mm = models.IntegerField(default=0)
    wall_cabinet_count = models.IntegerField(default=0)
    work_top_length_mm = models.IntegerField(default=0)  # Can override global setting
    
    # Cost Breakdown
    led_under_wall_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    led_work_top_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    led_skirting_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    spot_lights_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = [
            ('project', 'cabinet_material', 'cabinet_type'),
        ]
    
    def calculate_costs(self):
        """Calculate all lighting costs based on rule and dimensions"""
        if not self.lighting_rule:
            return
            
        rule = self.lighting_rule
        led_rate = rule.led_strip_rate_per_mm
        spot_rate = rule.spot_light_rate_per_cabinet
        
        # Reset costs
        self.led_under_wall_cost = Decimal('0')
        self.led_work_top_cost = Decimal('0') 
        self.led_skirting_cost = Decimal('0')
        self.spot_lights_cost = Decimal('0')
        
        # LED under wall cabinets
        if rule.applies_to_wall_cabinets and self.wall_cabinet_width_mm > 0:
            self.led_under_wall_cost = self.wall_cabinet_width_mm * led_rate
            
        # LED on work top nosing  
        if rule.applies_to_wall_cabinets and self.work_top_length_mm > 0:
            self.led_work_top_cost = self.work_top_length_mm * led_rate
            
        # LED skirting (luxury tier only)
        if (rule.budget_tier == 'LUXURY' and 
            rule.applies_to_base_cabinets and 
            self.base_cabinet_width_mm > 0):
            self.led_skirting_cost = self.base_cabinet_width_mm * led_rate
            
        # Spot lights
        if rule.applies_to_wall_cabinets and self.wall_cabinet_count > 0:
            self.spot_lights_cost = self.wall_cabinet_count * spot_rate
            
        # Total for this item
        self.total_cost = (
            self.led_under_wall_cost + 
            self.led_work_top_cost + 
            self.led_skirting_cost + 
            self.spot_lights_cost
        )
        
    def save(self, *args, **kwargs):
        self.calculate_costs()
        super().save(*args, **kwargs)
    
    def __str__(self):
        type_str = f" - {self.cabinet_type.name}" if self.cabinet_type else ""
        return f"{self.project} - {self.cabinet_material.name}{type_str}"


# Helper functions for the enhanced structure

def get_applicable_lighting_rules(project, cabinet_material=None, cabinet_type=None):
    """Get lighting rules applicable to a project"""
    rules = LightingRules.objects.filter(
        models.Q(is_global=True) | models.Q(customer=project.customer),
        budget_tier=project.budget_tier,
        is_active=True
    )
    
    if cabinet_material:
        rules = rules.filter(cabinet_material=cabinet_material)
    
    if cabinet_type:
        rules = rules.filter(
            models.Q(cabinet_type=cabinet_type) | models.Q(cabinet_type__isnull=True)
        )
    
    # Order by specificity: customer-specific first, then type-specific, then general
    return rules.order_by(
        models.Case(
            models.When(customer=project.customer, then=models.Value(0)),
            default=models.Value(1)
        ),
        models.Case(
            models.When(cabinet_type__isnull=False, then=models.Value(0)),
            default=models.Value(1)
        ),
        '-effective_from'
    )


def calculate_project_lighting_totals(project):
    """Calculate total lighting costs from all active lighting items"""
    config, created = ProjectLightingConfiguration.objects.get_or_create(
        project=project,
        defaults={'work_top_length_mm': 6000}  # Default value
    )
    
    # Calculate totals from line items
    wall_items = project.lines.filter(cabinet_type__category__name='WALL')
    base_items = project.lines.filter(cabinet_type__category__name='BASE')
    
    config.total_wall_cabinet_width_mm = sum(item.width_mm * item.qty for item in wall_items)
    config.total_base_cabinet_width_mm = sum(item.width_mm * item.qty for item in base_items)
    config.total_wall_cabinet_count = sum(item.qty for item in wall_items)
    
    # Calculate grand total from all lighting items
    active_items = project.lighting_items.filter(is_active=True)
    config.grand_total_lighting_cost = sum(item.total_cost for item in active_items)
    
    config.save()
    return config


def auto_create_lighting_items_for_project(project):
    """Automatically create lighting items based on project line items"""
    # Get unique material/type combinations from line items
    combinations = project.lines.values(
        'cabinet_material', 'cabinet_type', 
        'cabinet_material__name', 'cabinet_type__name'
    ).distinct()
    
    created_items = []
    
    for combo in combinations:
        material_id = combo['cabinet_material']
        type_id = combo['cabinet_type']
        
        # Check if lighting item already exists
        existing = project.lighting_items.filter(
            cabinet_material_id=material_id,
            cabinet_type_id=type_id
        ).first()
        
        if existing:
            continue
            
        # Find applicable rule
        material = Materials.objects.get(id=material_id)
        cabinet_type = CabinetTypes.objects.get(id=type_id) if type_id else None
        
        rules = get_applicable_lighting_rules(project, material, cabinet_type)
        rule = rules.first()
        
        if not rule:
            continue
            
        # Calculate dimensions for this material/type combination
        relevant_items = project.lines.filter(
            cabinet_material_id=material_id,
            cabinet_type_id=type_id
        )
        
        wall_items = relevant_items.filter(cabinet_type__category__name='WALL')
        base_items = relevant_items.filter(cabinet_type__category__name='BASE')
        
        wall_width = sum(item.width_mm * item.qty for item in wall_items)
        base_width = sum(item.width_mm * item.qty for item in base_items)
        wall_count = sum(item.qty for item in wall_items)
        
        # Create lighting item
        lighting_item = ProjectLightingItem.objects.create(
            project=project,
            lighting_rule=rule,
            cabinet_material=material,
            cabinet_type=cabinet_type,
            wall_cabinet_width_mm=wall_width,
            base_cabinet_width_mm=base_width,
            wall_cabinet_count=wall_count,
            work_top_length_mm=wall_width if wall_width > 0 else 0  # Default to wall width
        )
        
        created_items.append(lighting_item)
    
    # Recalculate project totals
    calculate_project_lighting_totals(project)
    
    return created_items

