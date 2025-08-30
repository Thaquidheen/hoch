from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import uuid
import os


def brand_logo_upload_path(instance, filename):
    """Generate upload path for brand logos"""
    return f'brands/logos/{instance.slug}/{filename}'


def product_image_upload_path(instance, filename):
    """Generate upload path for product images"""
    return f'products/{instance.product_variant.product.category.slug}/{instance.product_variant.product.slug}/{filename}'


class BaseModel(models.Model):
    """Abstract base model with common fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Category(BaseModel):
    """Product categories: Tall Unit, Base Unit, Wall Unit, Organizer, Hardware"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['sort_order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Brand(BaseModel):
    """Brands: Blum, Hafele, Hettich, Kessbohmer, etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to=brand_logo_upload_path, blank=True, null=True)
    website = models.URLField(blank=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class CategoryBrand(BaseModel):
    """Many-to-Many relationship between categories and brands"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['category', 'brand']
        verbose_name = "Category Brand"
        verbose_name_plural = "Category Brands"
    
    def __str__(self):
        return f"{self.category.name} - {self.brand.name}"





class Color(BaseModel):
    """Available colors for products"""
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, blank=True)  # #FFFFFF format
    image = models.ImageField(upload_to='colors/', blank=True, null=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ProductSize(BaseModel):
    """Standard sizes for different categories"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # e.g., "300mm", "600mm"
    width = models.DecimalField(max_digits=8, decimal_places=2)  # in mm
    height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_standard = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['category', 'name']
        ordering = ['category', 'width']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Product(BaseModel):
    """Main product table"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    
    # SEO and meta fields
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['category', 'brand', 'name']
        ordering = ['category', 'brand', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand.name}-{self.name}")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.brand.name} - {self.name}"


def variant_image_upload_path(instance, filename):
    """Generate upload path for variant images"""
    # Create unique filename with material code
    ext = filename.split('.')[-1]
    filename = f"{instance.material_code}_{uuid.uuid4().hex[:8]}.{ext}"
    return f'variants/{instance.product.category.slug}/{instance.product.slug}/{filename}'

class ProductVariant(BaseModel):
    """Product variants with size, color, pricing, and images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    # Simplified size inputs
    size_width = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Width in mm"
    )
    size_height = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Height in mm"
    )
    size_depth = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Depth in mm"
    )
    
    # Simplified color input
    color_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Color name (e.g., Stainless Steel Silver)"
    )
    
    # Material code - unique identifier
    material_code = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Enter material code manually"
    )
    

    image = models.ImageField(
        upload_to=variant_image_upload_path,
        null=True,
        blank=True,
        help_text="Primary image for this variant"
    )
    
    # Pricing fields (backend auto-calculates derived values)
    mrp = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Maximum Retail Price"
    )
    
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('18.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Tax percentage (default 18%)"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated tax amount (auto-calculated)"
    )
    
    discount_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Discount percentage"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated discount amount (auto-calculated)"
    )
    
    company_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Final company price (auto-calculated: MRP + Tax - Discount)"
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)
    sku_code = models.CharField(max_length=100, unique=True, blank=True)
    
    # Additional specifications
    specifications = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['product', 'material_code']
        ordering = ['product', 'material_code']
    
    def save(self, *args, **kwargs):
        # Calculate tax amount: tax_rate% of MRP
        self.tax_amount = (self.mrp * self.tax_rate) / 100
        
        # Calculate discount amount
        self.discount_amount = (self.mrp * self.discount_rate) / 100
        
        # Calculate company price: MRP + Tax - Discount
        self.company_price = self.mrp + self.tax_amount - self.discount_amount
        
        # Auto-generate SKU if not provided
        if not self.sku_code:
            self.sku_code = self.material_code
        
        super().save(*args, **kwargs)
    
    @property
    def dimensions_display(self):
        """Display dimensions as a string"""
        dims = []
        if self.size_width:
            dims.append(f"W:{self.size_width}")
        if self.size_height:
            dims.append(f"H:{self.size_height}")
        if self.size_depth:
            dims.append(f"D:{self.size_depth}")
        return " × ".join(dims) + "mm" if dims else "Custom"
    
    @property
    def price_breakdown(self):
        """Return detailed price breakdown"""
        return {
            'mrp': float(self.mrp),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'discount_rate': float(self.discount_rate),
            'discount_amount': float(self.discount_amount),
            'company_price': float(self.company_price),
            'savings': float(self.discount_amount)
        }
    
    @property
    def image_url(self):
        """Get absolute URL for variant image"""
        if self.image:
            return self.image.url
        return None
    
    def __str__(self):
        return f"{self.product.name} - {self.color_name} - {self.dimensions_display} ({self.material_code})"

class ProductImage(BaseModel):
    """Multiple images for product variants"""
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=product_image_upload_path)
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    @property
    def primary_image_url(self):
        """For a single image instance, just return its own URL."""
        return self.image.url if self.image else None
    
    class Meta:
        ordering = ['sort_order', 'id']
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per variant
        if self.is_primary:
            ProductImage.objects.filter(
                product_variant=self.product_variant, 
                is_primary=True
            ).update(is_primary=False)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Image for {self.product_variant}"

