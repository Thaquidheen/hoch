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


class ProductVariant(BaseModel):
    """Product variants with size, color, and pricing - each variant has its own material code"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(ProductSize, on_delete=models.CASCADE, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True, blank=True)
    
    # Custom dimensions if not using standard size
    custom_width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    custom_height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    custom_depth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Admin manually enters material code - NO auto generation
    material_code = models.CharField(max_length=50, unique=True, help_text="Enter material code manually")
    
    # Pricing - all manual entry, NO calculations
    mrp = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tax_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    # Final value entered manually by admin
    value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Final value/selling price - enter manually"
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)
    sku_code = models.CharField(max_length=100, unique=True, blank=True)
    
    # Additional specifications
    specifications = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['product', 'size', 'color']
        ordering = ['product', 'size', 'color']
    
    def save(self, *args, **kwargs):
        # Only generate SKU if not provided (can be same as material code)
        if not self.sku_code:
            self.sku_code = self.material_code
        super().save(*args, **kwargs)
    
    @property
    def dimensions(self):
        """Get dimensions (either standard or custom)"""
        if self.size:
            return {
                'width': self.size.width,
                'height': self.size.height,
                'depth': self.size.depth
            }
        return {
            'width': self.custom_width,
            'height': self.custom_height,
            'depth': self.custom_depth
        }
    
    @property
    def primary_image_url(self):
        """Primary image URL for this variant (fallback to first image)."""
        img = self.images.filter(is_primary=True).first() or self.images.order_by('sort_order', 'id').first()
        return img.image.url if img and img.image else None
    
    def __str__(self):
        size_str = self.size.name if self.size else "Custom"
        color_str = self.color.name if self.color else "Default"
        return f"{self.product.name} - {size_str} - {color_str} ({self.material_code})"


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

