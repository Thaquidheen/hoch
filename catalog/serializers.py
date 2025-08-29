from rest_framework import serializers
from decimal import Decimal
from .models import *
from customers.models import Customer



# ============================================================================
# Basic Entity Serializers
# ============================================================================

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories"""
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'sort_order', 'is_active', 'created_at']
        read_only_fields = ['slug', 'created_at']


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for brands"""
    
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'description', 'logo', 'logo_url', 'website', 'is_active', 'created_at']
        read_only_fields = ['slug', 'created_at']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None


class ColorSerializer(serializers.ModelSerializer):
    """Serializer for colors"""
    
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code', 'image', 'image_url', 'is_active']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None


class ProductSizeSerializer(serializers.ModelSerializer):
    """Serializer for product sizes"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    dimensions_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductSize
        fields = [
            'id', 'category', 'category_name', 'name', 'width', 'height', 'depth',
            'is_standard', 'dimensions_display', 'is_active'
        ]
    
    def get_dimensions_display(self, obj):
        dims = []
        if obj.width:
            dims.append(f"W:{obj.width}")
        if obj.height:
            dims.append(f"H:{obj.height}")
        if obj.depth:
            dims.append(f"D:{obj.depth}")
        return " × ".join(dims) + "mm" if dims else "Custom"


# ============================================================================
# Product Related Serializers
# ============================================================================

class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""
    
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'alt_text', 'is_primary', 'sort_order']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None




class ProductVariantSerializer(serializers.ModelSerializer):
    """Detailed serializer for product variants with image support"""

    product_name = serializers.CharField(source='product.name', read_only=True)
    brand_name = serializers.CharField(source='product.brand.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)

    # Calculated fields (read-only)
    dimensions_display = serializers.SerializerMethodField()
    price_breakdown = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    # Price calculation fields (read-only - calculated automatically)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    company_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'product_name', 'brand_name', 'category_name',
            
            # Size fields (simplified)
            'size_width', 'size_height', 'size_depth', 'dimensions_display',
            
            # Color field (simplified)
            'color_name',
            
            # Material code
            'material_code',
            
            # NEW: Image field
            'image', 'image_url',
            
            # Pricing fields
            'mrp', 'tax_rate', 'tax_amount', 'discount_rate', 'discount_amount', 'company_price',
            'price_breakdown',
            
            # Stock and other fields
            'stock_quantity', 'sku_code', 'specifications',
            
            # Meta
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'tax_amount', 'discount_amount', 'company_price', 
            'created_at', 'updated_at'
        ]
    
    def get_dimensions_display(self, obj):
        return obj.dimensions_display
    
    def get_price_breakdown(self, obj):
        return obj.price_breakdown
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def validate_mrp(self, value):
        """Validate MRP is positive"""
        if value <= 0:
            raise serializers.ValidationError("MRP must be greater than 0")
        return value
    
    def validate_discount_rate(self, value):
        """Validate discount rate is between 0-100"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Discount rate must be between 0 and 100")
        return value
    
    def validate_tax_rate(self, value):
        """Validate tax rate is between 0-100"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Tax rate must be between 0 and 100")
        return value
    
    def validate_material_code(self, value):
        """Validate material code uniqueness"""
        if ProductVariant.objects.filter(
            material_code=value
        ).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Material code must be unique")
        return value


class ProductVariantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product variant lists with image"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    brand_name = serializers.CharField(source='product.brand.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    dimensions_display = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product_name', 'brand_name', 'category_name',
            'color_name', 'dimensions_display', 'material_code',
            'mrp', 'discount_rate', 'tax_rate', 'company_price',
            'stock_quantity', 'image_url', 'is_active'
        ]
    
    def get_dimensions_display(self, obj):
        return obj.dimensions_display
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products with variants - Simple Fix"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    
    # Make these fields NOT read_only, but handle representation separately
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())
    
    variants = ProductVariantListSerializer(many=True, read_only=True)
    
    # Calculated fields
    variants_count = serializers.SerializerMethodField()
    price_range = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_name', 'brand', 'brand_name',
            'name', 'slug', 'description', 'meta_title', 'meta_description',
            'variants', 'variants_count', 'price_range',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Override to return full nested objects for reading"""
        data = super().to_representation(instance)
        
        # Replace the IDs with full objects for frontend consumption
        data['category'] = CategorySerializer(instance.category).data if instance.category else None
        data['brand'] = BrandSerializer(instance.brand).data if instance.brand else None
        
        return data
    
    def get_variants_count(self, obj):
        return obj.variants.filter(is_active=True).count()
    
    def get_price_range(self, obj):
        variants = obj.variants.filter(is_active=True)
        if variants:
            prices = [float(v.value) for v in variants]
            min_price = min(prices)
            max_price = max(prices)
            if min_price == max_price:
                return f"₹{min_price:,.2f}"
            return f"₹{min_price:,.2f} - ₹{max_price:,.2f}"
        return "No variants"

class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    variants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'category_name', 'brand_name', 'name', 'slug',
            'variants_count', 'is_active', 'created_at'
        ]
    
    def get_variants_count(self, obj):
        return obj.variants.filter(is_active=True).count()


class PriceCalculationSerializer(serializers.Serializer):
    """Serializer for price calculations without saving"""
    mrp = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tax_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('18.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    discount_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    def validate(self, data):
        """Calculate all price-related fields"""
        mrp = data['mrp']
        tax_rate = data.get('tax_rate', Decimal('18.00'))
        discount_rate = data.get('discount_rate', Decimal('0.00'))
        
        # Calculate tax amount
        tax_amount = (mrp * tax_rate) / 100
        
        # Calculate discount amount
        discount_amount = (mrp * discount_rate) / 100
        
        # Calculate company price
        company_price = mrp + tax_amount - discount_amount
        
        # Add calculated fields to response
        data['tax_amount'] = tax_amount
        data['discount_amount'] = discount_amount
        data['company_price'] = company_price
        
        return data


# ============================================================================
# Specialized Serializers for API Responses
# ============================================================================

class CategoryBrandSerializer(serializers.ModelSerializer):
    """Serializer for category-brand relationships"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    
    class Meta:
        model = CategoryBrand
        fields = ['id', 'category', 'category_name', 'brand', 'brand_name', 'is_active']



class ProductSearchSerializer(serializers.Serializer):
    """Serializer for product search functionality"""
    
    query = serializers.CharField(max_length=200, required=False)
    category = serializers.IntegerField(required=False)
    brand = serializers.IntegerField(required=False)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    in_stock = serializers.BooleanField(default=False)
    
    def validate(self, data):
        if data.get('min_price') and data.get('max_price'):
            if data['min_price'] > data['max_price']:
                raise serializers.ValidationError("Min price cannot be greater than max price")
        return data



class CatalogStatsSerializer(serializers.Serializer):
    """Serializer for catalog statistics"""
    
    total_products = serializers.IntegerField(read_only=True)
    total_variants = serializers.IntegerField(read_only=True)
    total_categories = serializers.IntegerField(read_only=True)
    total_brands = serializers.IntegerField(read_only=True)
    low_stock_count = serializers.IntegerField(read_only=True)
    out_of_stock_count = serializers.IntegerField(read_only=True)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    # Category breakdown
    category_breakdown = serializers.ListField(child=serializers.DictField(), read_only=True)
    brand_breakdown = serializers.ListField(child=serializers.DictField(), read_only=True)





