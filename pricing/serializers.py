from rest_framework import serializers
from decimal import Decimal
from .models import (
    GeometryRule, Project, ProjectLineItem, ProjectLineItemAccessory,
    ProjectTotals, ProjectPlanImage, CabinetTypes, Materials, Accessories, 
    FinishRates, DoorFinishRates, CabinetTypeBrandCharge,
    LightingRules, ProjectLightingItem, ProjectLightingConfiguration
)

from catalog.models import Brand
from catalog.models import Category
from customers.models import Customer
from customers.serializers import CustomerSerializer
from catalog.serializers import  CategorySerializer
from catalog.serializers import BrandSerializer





class MaterialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materials
        fields = [
            'id', 'name', 'role', 'notes',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FinishRatesSerializer(serializers.ModelSerializer):
    material_detail = MaterialsSerializer(source='material', read_only=True)

    class Meta:
        model = FinishRates
        fields = [
            'id', 'material', 'material_detail', 'budget_tier',
            'unit_rate', 'currency', 'effective_from', 'effective_to',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DoorFinishRatesSerializer(serializers.ModelSerializer):
    material_detail = MaterialsSerializer(source='material', read_only=True)

    class Meta:
        model = DoorFinishRates
        fields = [
            'id', 'material', 'material_detail',
            'unit_rate', 'currency', 'effective_from', 'effective_to',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CabinetTypesSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)

    class Meta:
        model = CabinetTypes
        fields = [
            'id', 'name', 'description', 'default_depth',
            'category', 'category_detail',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CabinetTypeBrandChargeSerializer(serializers.ModelSerializer):
    cabinet_type_detail = CabinetTypesSerializer(source='cabinet_type', read_only=True)

    class Meta:
        model = CabinetTypeBrandCharge
        fields = [
            'id', 'cabinet_type', 'cabinet_type_detail', 'brand_name',
            'standard_accessory_charge', 'currency',
            'effective_from', 'effective_to',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_standard_accessory_charge(self, value):
        """Ensure the charge is positive"""
        if value < 0:
            raise serializers.ValidationError("Standard accessory charge must be positive")
        return value


class AccessoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessories
        fields = [
            'id', 'name', 'description', 'unit_price', 'currency',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']








class GeometryRuleSerializer(serializers.ModelSerializer):
    cabinet_type_detail = CabinetTypesSerializer(source='cabinet_type', read_only=True)

    class Meta:
        model = GeometryRule
        fields = [
            'id', 'cabinet_type', 'cabinet_type_detail', 
            'formula_cabinet_sqft', 'formula_door_sqft', 'parameters',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    customer_detail = CustomerSerializer(source='customer', read_only=True)
    brand_detail = BrandSerializer(source='brand', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'customer', 'customer_detail', 'brand', 'brand_detail',
            'budget_tier', 'margin_pct', 'gst_pct', 'currency', 'status',
            'scopes', 'notes',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_margin_pct(self, value):
        """Validate margin percentage"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Margin percentage must be between 0 and 100")
        return value

    def validate_gst_pct(self, value):
        """Validate GST percentage"""
        if value < 0 or value > 50:
            raise serializers.ValidationError("GST percentage must be between 0 and 50")
        return value


class ProjectLineItemAccessorySerializer(serializers.ModelSerializer):
    accessory_detail = AccessoriesSerializer(source='accessory', read_only=True)

    class Meta:
        model = ProjectLineItemAccessory
        fields = [
            'id', 'line_item', 'accessory', 'accessory_detail',
            'qty', 'unit_price', 'tax_rate_snapshot', 'total_price',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_qty(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


class ProjectLineItemSerializer(serializers.ModelSerializer):
    cabinet_type_detail = CabinetTypesSerializer(source='cabinet_type', read_only=True)
    cabinet_material_detail = MaterialsSerializer(source='cabinet_material', read_only=True)
    door_material_detail = MaterialsSerializer(source='door_material', read_only=True)
    # Read-only nested accessories
    extra_accessories = ProjectLineItemAccessorySerializer(many=True, read_only=True)

    class Meta:
        model = ProjectLineItem
        fields = [
            'id', 'project', 'scope', 'cabinet_type', 'cabinet_type_detail', 'qty',
            'width_mm', 'depth_mm', 'height_mm',
            'cabinet_material', 'cabinet_material_detail',
            'door_material', 'door_material_detail',
            'computed_cabinet_sqft', 'computed_door_sqft',
            'cabinet_unit_rate', 'door_unit_rate',
            'cabinet_material_price', 'standard_accessory_charge',
            'door_price', 'top_price',
            'line_total_before_tax', 'currency', 'remarks',
            'extra_accessories',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Custom validation for the entire serializer"""
        # Ensure correct material roles
        cab = data.get('cabinet_material') or getattr(self.instance, 'cabinet_material', None)
        door = data.get('door_material') or getattr(self.instance, 'door_material', None)
        
        if cab and cab.role not in ('CABINET', 'BOTH'):
            raise serializers.ValidationError({
                'cabinet_material': 'Material role must be CABINET or BOTH.'
            })
        
        if door and door.role not in ('DOOR', 'BOTH'):
            raise serializers.ValidationError({
                'door_material': 'Material role must be DOOR or BOTH.'
            })
        
        # Validate positive dimensions and quantities
        for field in ('width_mm', 'depth_mm', 'height_mm', 'qty'):
            value = data.get(field) if field in data else getattr(self.instance, field, None)
            if value is not None and int(value) <= 0:
                raise serializers.ValidationError({
                    field: 'Must be greater than 0'
                })
        
        return data

    def validate_width_mm(self, value):
        """Validate width is reasonable"""
        if value < 50 or value > 5000:
            raise serializers.ValidationError("Width must be between 50mm and 5000mm")
        return value

    def validate_depth_mm(self, value):
        """Validate depth is reasonable"""
        if value < 50 or value > 1000:
            raise serializers.ValidationError("Depth must be between 50mm and 1000mm")
        return value

    def validate_height_mm(self, value):
        """Validate height is reasonable"""
        if value < 50 or value > 3000:
            raise serializers.ValidationError("Height must be between 50mm and 3000mm")
        return value


class ProjectTotalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTotals
        fields = [
            'id', 'project', 'subtotal_cabinets', 'subtotal_doors',
            'subtotal_accessories', 'subtotal_tops', 'margin_amount',
            'taxable_amount', 'gst_amount', 'grand_total', 'currency',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectPlanImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlanImage
        fields = [
            'id', 'project', 'image', 'caption', 'sort_order',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_sort_order(self, value):
        """Validate sort order is not negative"""
        if value < 0:
            raise serializers.ValidationError("Sort order cannot be negative")
        return value


# Additional serializers for different use cases

class CabinetTypesSimpleSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdown lists"""
    class Meta:
        model = CabinetTypes
        fields = ['id', 'name', 'description', 'default_depth']


class MaterialsSimpleSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdown lists"""
    class Meta:
        model = Materials
        fields = ['id', 'name', 'role']


class BrandSimpleSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdown lists"""
    class Meta:
        model = Brand
        fields = ['id', 'name', 'category']


class ProjectSummarySerializer(serializers.ModelSerializer):
    """Serializer for project list views"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    total_amount = serializers.DecimalField(
        source='totals.grand_total', 
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = Project
        fields = [
            'id', 'customer_name', 'brand_name', 'budget_tier',
            'status', 'total_amount', 'currency',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']




class LightingRulesSerializer(serializers.ModelSerializer):
    material_detail = MaterialsSerializer(source='cabinet_material', read_only=True)
    cabinet_type_detail = CabinetTypesSerializer(source='cabinet_type', read_only=True)
    customer_detail = CustomerSerializer(source='customer', read_only=True)
    
    class Meta:
        model = LightingRules
        fields = [
            'id', 'name', 'customer', 'customer_detail', 'is_global',
            'cabinet_material', 'material_detail', 'cabinet_type', 'cabinet_type_detail',
            'budget_tier', 'calc_method', 'led_strip_rate_per_mm', 'spot_light_rate_per_cabinet',
            'led_specification', 'spot_light_specification',
            'applies_to_wall_cabinets', 'applies_to_base_cabinets',
            'effective_from', 'effective_to', 'currency',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate customer-specific rules
        if not data.get('is_global') and not data.get('customer'):
            raise serializers.ValidationError("Customer-specific rules must specify a customer")
        
        if data.get('is_global') and data.get('customer'):
            raise serializers.ValidationError("Global rules cannot be customer-specific")
            
        return data


class ProjectLightingItemSerializer(serializers.ModelSerializer):
    lighting_rule_detail = LightingRulesSerializer(source='lighting_rule', read_only=True)
    material_detail = MaterialsSerializer(source='cabinet_material', read_only=True)
    cabinet_type_detail = CabinetTypesSerializer(source='cabinet_type', read_only=True)
    
    # Calculated fields
    led_strips_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_linear_meters = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    class Meta:
        model = ProjectLightingItem
        fields = [
            'id', 'project', 'lighting_rule', 'lighting_rule_detail',
            'cabinet_material', 'material_detail', 'cabinet_type', 'cabinet_type_detail',
            'wall_cabinet_width_mm', 'base_cabinet_width_mm', 'wall_cabinet_count', 'work_top_length_mm',
            'led_under_wall_cost', 'led_work_top_cost', 'led_skirting_cost', 'spot_lights_cost', 'total_cost',
            'led_strips_total', 'total_linear_meters',
            'is_active', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'led_under_wall_cost', 'led_work_top_cost', 'led_skirting_cost', 
            'spot_lights_cost', 'total_cost', 'created_at', 'updated_at'
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Add calculated fields
        data['led_strips_total'] = (
            instance.led_under_wall_cost + 
            instance.led_work_top_cost + 
            instance.led_skirting_cost
        )
        
        total_mm = (
            instance.wall_cabinet_width_mm + 
            instance.base_cabinet_width_mm + 
            instance.work_top_length_mm
        )
        data['total_linear_meters'] = round(total_mm / 1000, 2) if total_mm > 0 else 0
        
        return data


class ProjectLightingConfigurationSerializer(serializers.ModelSerializer):
    lighting_items = ProjectLightingItemSerializer(source='project.lighting_items', many=True, read_only=True)
    active_items_count = serializers.SerializerMethodField()
    total_led_cost = serializers.SerializerMethodField()
    total_spot_cost = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectLightingConfiguration
        fields = [
            'id', 'project', 'work_top_length_mm',
            'total_wall_cabinet_width_mm', 'total_base_cabinet_width_mm', 'total_wall_cabinet_count',
            'grand_total_lighting_cost', 'currency',
            'lighting_items', 'active_items_count', 'total_led_cost', 'total_spot_cost',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_wall_cabinet_width_mm', 'total_base_cabinet_width_mm', 
            'total_wall_cabinet_count', 'grand_total_lighting_cost', 'created_at', 'updated_at'
        ]
    
    def get_active_items_count(self, obj):
        return obj.project.lighting_items.filter(is_active=True).count()
    
    def get_total_led_cost(self, obj):
        items = obj.project.lighting_items.filter(is_active=True)
        return sum(
            item.led_under_wall_cost + item.led_work_top_cost + item.led_skirting_cost 
            for item in items
        )
    
    def get_total_spot_cost(self, obj):
        items = obj.project.lighting_items.filter(is_active=True)
        return sum(item.spot_lights_cost for item in items)