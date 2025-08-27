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
    """Detailed serializer for product variants"""

    product_name = serializers.CharField(source='product.name', read_only=True)
    brand_name = serializers.CharField(source='product.brand.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    size_display = serializers.CharField(source='size.name', read_only=True)
    color_display = serializers.CharField(source='color.name', read_only=True)

    # Read-only nested representations
    size = ProductSizeSerializer(read_only=True)
    color = ColorSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)  # <-- make images nested read-only

    # Write-only inputs for setting relations
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductSize.objects.all(), write_only=True, required=False, allow_null=True
    )
    color_id = serializers.PrimaryKeyRelatedField(
        queryset=Color.objects.all(), write_only=True, required=False, allow_null=True
    )

    # Calculated fields
    dimensions_display = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    price_after_discount = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'product_name', 'brand_name', 'category_name',
            'size', 'size_display', 'size_id',
            'color', 'color_display', 'color_id',
            'custom_width', 'custom_height', 'custom_depth', 'dimensions_display',
            'material_code', 'mrp', 'tax_percentage', 'discount_percentage', 'value',
            'final_price', 'discount_amount', 'price_after_discount',
            'stock_quantity', 'sku_code', 'specifications',
            'images',                 # kept as read-only nested
            'is_active', 'created_at', 'updated_at', 'primary_image'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        size = validated_data.pop('size_id', None)
        color = validated_data.pop('color_id', None)
        obj = super().create(validated_data)
        # assign FKs if provided
        if size is not None:
            obj.size = size
        if color is not None:
            obj.color = color
        obj.save(update_fields=['size', 'color'])
        return obj

    def update(self, instance, validated_data):
        size = validated_data.pop('size_id', None)
        color = validated_data.pop('color_id', None)
        obj = super().update(instance, validated_data)
        changed = []
        if 'size_id' in self.initial_data:
            obj.size = size
            changed.append('size')
        if 'color_id' in self.initial_data:
            obj.color = color
            changed.append('color')
        if changed:
            obj.save(update_fields=changed)
        return obj

    def get_primary_image(self, obj):
        url = getattr(obj, 'primary_image_url', None)
        req = self.context.get('request')
        return req.build_absolute_uri(url) if req and url else url
    
    def get_dimensions_display(self, obj):
        dims = obj.dimensions
        parts = []
        if dims['width']:
            parts.append(f"W:{dims['width']}")
        if dims['height']:
            parts.append(f"H:{dims['height']}")
        if dims['depth']:
            parts.append(f"D:{dims['depth']}")
        return " × ".join(parts) + "mm" if parts else "Custom"
    
    def get_final_price(self, obj):
        """Final selling price (same as value field)"""
        return float(obj.value)
    
    def get_discount_amount(self, obj):
        """Calculate discount amount"""
        return float(obj.mrp * obj.discount_percentage / 100)
    
    def get_price_after_discount(self, obj):
        """Price after discount (before tax)"""
        return float(obj.mrp - (obj.mrp * obj.discount_percentage / 100))
    
    def validate_material_code(self, value):
        """Validate material code uniqueness"""
        if ProductVariant.objects.filter(material_code=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Material code must be unique")
        return value


class ProductVariantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product variant lists"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    brand_name = serializers.CharField(source='product.brand.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    size_display = serializers.CharField(source='size.name', read_only=True)
    color_display = serializers.CharField(source='color.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product_name', 'brand_name', 'category_name',
            'size_display', 'color_display', 'material_code',
            'mrp', 'discount_percentage', 'tax_percentage',  # <-- added
            'value', 'stock_quantity', 'primary_image', 'is_active'
        ]
    
    def get_primary_image(self, obj):
        url = getattr(obj, 'primary_image_url', None) or (obj.images.order_by('sort_order', 'id').first().image.url if obj.images.exists() else None)
        req = self.context.get('request')
        return req.build_absolute_uri(url) if req and url else url


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





