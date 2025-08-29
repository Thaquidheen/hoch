from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F, Q, Case, When, Value
from django.utils.timezone import now
from django.db import transaction
# from rest_framework import viewsets, status
from rest_framework.decorators import action

from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, filters

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from .models import *
from .serializers import (
    GeometryRuleSerializer, ProjectLightingConfigurationSerializer, ProjectPlanImageGroupListSerializer, ProjectPlanImageGroupSerializer, ProjectSerializer, ProjectLineItemSerializer,
    ProjectLineItemAccessorySerializer, ProjectTotalsSerializer, 
    ProjectPlanImageSerializer, MaterialsSerializer, FinishRatesSerializer,
    DoorFinishRatesSerializer, CabinetTypesSerializer, 
    CabinetTypeBrandChargeSerializer, AccessoriesSerializer,
    BrandSerializer, CustomerSerializer, CategorySerializer,
    LightingRulesSerializer,ProjectLightingItemSerializer
)


# =========================
# Helper Functions
# =========================

def _active_on(qs, eff_date: date):
    """Filter queryset for records active on given date"""
    return qs.filter(
        effective_from__lte=eff_date
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=eff_date)
    )


def _cabinet_rate(material, tier, eff_date):
    """Get cabinet material rate for given tier and date"""
    row = _active_on(
        FinishRates.objects.filter(material=material, budget_tier=tier), 
        eff_date
    ).order_by('-effective_from').first()
    return Decimal(row.unit_rate) if row else Decimal('0')


def _door_rate(material, eff_date):
    """Get door material rate for given date"""
    row = _active_on(
        DoorFinishRates.objects.filter(material=material), 
        eff_date
    ).order_by('-effective_from').first()
    return Decimal(row.unit_rate) if row else Decimal('0')


def _brand_base(cabinet_type, brand_name, eff_date):
    """Get brand base charge for cabinet type and date"""
    row = _active_on(
        CabinetTypeBrandCharge.objects.filter(
            cabinet_type=cabinet_type, 
            brand_name=brand_name
        ), 
        eff_date
    ).order_by('-effective_from').first()
    return Decimal(row.standard_accessory_charge) if row else Decimal('0')


def compute_sqft(cabinet_type, w, d, h):
    """Compute cabinet and door square footage based on dimensions"""
    # Fetch active rule; implement your own parser/evaluator for formula strings
    rule = GeometryRule.objects.filter(
        cabinet_type=cabinet_type, 
        is_active=True
    ).order_by('-created_at').first()
    
    # Example: scale from baseline parameters if provided
    p = (rule.parameters or {}) if rule else {}
    base_w = Decimal(p.get('base_w_mm', 450))
    base_d = Decimal(p.get('base_d_mm', 600))
    base_h = Decimal(p.get('base_h_mm', 850))
    base_cabinet_sqft = Decimal(p.get('base_cabinet_sqft', '21.0190876039'))
    base_door_sqft = Decimal(p.get('base_door_sqft', '4.1388936981'))
    
    w = Decimal(w)
    d = Decimal(d)
    h = Decimal(h)
    
    scale_cab = (w/base_w) * (d/base_d) * (h/base_h)
    scale_door = (w/base_w) * (h/base_h)
    
    cab_sqft = (base_cabinet_sqft * scale_cab).quantize(Decimal('0.0001'))
    door_sqft = (base_door_sqft * scale_door).quantize(Decimal('0.0001'))
    
    return cab_sqft, door_sqft


def compute_line(line: ProjectLineItem, eff_date=None):
    """Compute all pricing for a project line item"""
    eff_date = eff_date or now().date()
    
    cab_sqft, door_sqft = compute_sqft(
        line.cabinet_type, 
        line.width_mm, 
        line.depth_mm, 
        line.height_mm
    )
    
    cab_rate = _cabinet_rate(line.cabinet_material, line.project.budget_tier, eff_date)
    door_rate = _door_rate(line.door_material, eff_date)
    base = _brand_base(line.cabinet_type, line.project.brand.name, eff_date)
    
    # Update computed fields
    line.computed_cabinet_sqft = cab_sqft
    line.computed_door_sqft = door_sqft
    line.cabinet_unit_rate = cab_rate
    line.door_unit_rate = door_rate
    
    line.cabinet_material_price = (cab_sqft * cab_rate * line.qty).quantize(Decimal('0.01'))
    line.door_price = (door_sqft * door_rate * line.qty).quantize(Decimal('0.01'))
    line.standard_accessory_charge = (base * line.qty).quantize(Decimal('0.01'))
    
    # Sum accessories linked to this line
    acc_sum = ProjectLineItemAccessory.objects.filter(
        line_item=line
    ).aggregate(s=Sum('total_price'))['s'] or Decimal('0')
    
    line.line_total_before_tax = (
        line.cabinet_material_price + 
        line.door_price + 
        line.standard_accessory_charge + 
        line.top_price + 
        acc_sum
    ).quantize(Decimal('0.01'))
    
    line.save()
    return line


def recompute_totals(project: Project):
    """Recompute project totals"""
    totals, _ = ProjectTotals.objects.get_or_create(project=project)
    lines = project.lines.all()
    
    acc_sum = ProjectLineItemAccessory.objects.filter(
        line_item__project=project
    ).aggregate(s=Sum('total_price'))['s'] or Decimal('0')
    
    subtotal_cabinets = (lines.aggregate(
        s=Sum(F('cabinet_material_price') + F('standard_accessory_charge'))
    )['s'] or Decimal('0'))
    
    subtotal_doors = (lines.aggregate(s=Sum('door_price'))['s'] or Decimal('0'))
    subtotal_tops = (lines.aggregate(s=Sum('top_price'))['s'] or Decimal('0'))
    
    # Update totals
    totals.subtotal_cabinets = subtotal_cabinets
    totals.subtotal_doors = subtotal_doors
    totals.subtotal_accessories = acc_sum
    totals.subtotal_tops = subtotal_tops
    
    subtotal = subtotal_cabinets + subtotal_doors + acc_sum + subtotal_tops
    margin_amount = (subtotal * (project.margin_pct/Decimal('100'))).quantize(Decimal('0.01'))
    taxable_amount = (subtotal + margin_amount).quantize(Decimal('0.01'))
    gst_amount = (taxable_amount * (project.gst_pct/Decimal('100'))).quantize(Decimal('0.01'))
    grand_total = (taxable_amount + gst_amount).quantize(Decimal('0.01'))
    
    totals.margin_amount = margin_amount
    totals.taxable_amount = taxable_amount
    totals.gst_amount = gst_amount
    totals.grand_total = grand_total
    totals.currency = project.currency
    totals.save()
    
    return totals


# =========================
# Base ViewSet
# =========================

class BaseModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['id']
    ordering_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


# =========================
# Masters & Rates ViewSets
# =========================

class CategoryViewSet(BaseModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ['name', 'description']


class MaterialsViewSet(BaseModelViewSet):
    queryset = Materials.objects.all()
    serializer_class = MaterialsSerializer
    search_fields = ['name', 'role', 'notes']


class FinishRatesViewSet(BaseModelViewSet):
    queryset = FinishRates.objects.all().select_related('material')
    serializer_class = FinishRatesSerializer
    search_fields = ['material__name', 'budget_tier']
    ordering_fields = ['unit_rate', 'effective_from', 'effective_to']
    
    def perform_create(self, serializer):
        eff_from = serializer.validated_data.get('effective_from')
        eff_to = serializer.validated_data.get('effective_to')
        if eff_to and eff_to < eff_from:
            raise ValueError('effective_to must be >= effective_from')
        serializer.save()
    
    def perform_update(self, serializer):
        self.perform_create(serializer)


class DoorFinishRatesViewSet(BaseModelViewSet):
    queryset = DoorFinishRates.objects.all().select_related('material')
    serializer_class = DoorFinishRatesSerializer
    search_fields = ['material__name']
    ordering_fields = ['unit_rate', 'effective_from', 'effective_to']
    
    def perform_create(self, serializer):
        eff_from = serializer.validated_data.get('effective_from')
        eff_to = serializer.validated_data.get('effective_to')
        if eff_to and eff_to < eff_from:
            raise ValueError('effective_to must be >= effective_from')
        serializer.save()
    
    def perform_update(self, serializer):
        self.perform_create(serializer)


class CabinetTypesViewSet(BaseModelViewSet):
    queryset = CabinetTypes.objects.all().select_related('category')
    serializer_class = CabinetTypesSerializer
    search_fields = ['name', 'description']


class CabinetTypeBrandChargeViewSet(BaseModelViewSet):
    queryset = CabinetTypeBrandCharge.objects.all().select_related('cabinet_type')
    serializer_class = CabinetTypeBrandChargeSerializer
    search_fields = ['cabinet_type__name', 'brand_name']
    ordering_fields = ['standard_accessory_charge', 'effective_from', 'effective_to']
    
    def perform_create(self, serializer):
        eff_from = serializer.validated_data.get('effective_from')
        eff_to = serializer.validated_data.get('effective_to')
        if eff_to and eff_to < eff_from:
            raise ValueError('effective_to must be >= effective_from')
        serializer.save()
    
    def perform_update(self, serializer):
        self.perform_create(serializer)


class AccessoriesViewSet(BaseModelViewSet):
    queryset = Accessories.objects.all()
    serializer_class = AccessoriesSerializer
    search_fields = ['name', 'description']
    ordering_fields = ['unit_price']


class BrandViewSet(BaseModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ['name', 'category', 'description']


class CustomerViewSet(BaseModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ['name', 'email', 'phone']


class GeometryRuleViewSet(BaseModelViewSet):
    queryset = GeometryRule.objects.all().select_related('cabinet_type')
    serializer_class = GeometryRuleSerializer
    search_fields = ['cabinet_type__name']


# =========================
# Project Management ViewSets
# =========================

class ProjectViewSet(BaseModelViewSet):
    queryset = Project.objects.all().select_related('customer', 'brand')
    serializer_class = ProjectSerializer
    search_fields = ['customer__name', 'status', 'brand__name']
    
    @action(detail=True, methods=['post'])
    def recalc(self, request, pk=None):
        """Recalculate all line items and project totals"""
        project = self.get_object()
        with transaction.atomic():
            for line in project.lines.all():
                compute_line(line)
            totals = recompute_totals(project)
        data = ProjectTotalsSerializer(totals).data
        return Response(data, status=status.HTTP_200_OK)
    @action(detail=True, methods=['get', 'post'])
    def lighting(self, request, pk=None):
        """Get or manage project lighting configuration"""
        project = self.get_object()
        
        if request.method == 'GET':
            config, created = ProjectLightingConfiguration.objects.get_or_create(
                project=project,
                defaults={'work_top_length_mm': 6000}
            )
            
            serializer = ProjectLightingConfigurationSerializer(config)
            return Response(serializer.data)
            
        elif request.method == 'POST':
            # Auto-create lighting items and return configuration
            config, created = ProjectLightingConfiguration.objects.get_or_create(
                project=project,
                defaults={'work_top_length_mm': 6000}
            )
            
            created_items = auto_create_lighting_items_for_project(project)
            
            serializer = ProjectLightingConfigurationSerializer(config)
            return Response({
                'configuration': serializer.data,
                'created_items': len(created_items),
                'message': f'Created {len(created_items)} lighting configurations'
            })
    
    @action(detail=True, methods=['post'])
    def recalculate_lighting(self, request, pk=None):
        """Recalculate all lighting costs for project"""
        project = self.get_object()
        
        with transaction.atomic():
            config = calculate_project_lighting_totals(project)
            
            # Also recalculate project totals to include lighting
            recalculate_project_totals(project.id)
            
        return Response({
            'message': 'Lighting costs recalculated',
            'grand_total_lighting_cost': config.grand_total_lighting_cost
        })


class ProjectLineItemViewSet(BaseModelViewSet):
    queryset = ProjectLineItem.objects.all().select_related(
        'project', 'cabinet_type', 'cabinet_material', 'door_material'
    ).prefetch_related('extra_accessories')
    serializer_class = ProjectLineItemSerializer
    search_fields = ['project__customer__name', 'cabinet_type__name', 'scope']
    ordering_fields = ['line_total_before_tax', 'created_at', 'updated_at']
    
    # ADD THIS METHOD:
    def get_queryset(self):
        """Filter line items by project if provided"""
        project_id = self.request.query_params.get('project')
        if project_id:
            return self.queryset.filter(project=project_id)
        return self.queryset
    
    def perform_create(self, serializer):
        line = serializer.save()
        compute_line(line)
        recompute_totals(line.project)
    
    @action(detail=True, methods=['post'])
    def compute(self, request, pk=None):
        """Recompute a specific line item"""
        line = self.get_object()
        compute_line(line)
        data = ProjectLineItemSerializer(line).data
        return Response(data, status=status.HTTP_200_OK)


class ProjectLineItemAccessoryViewSet(BaseModelViewSet):
    queryset = ProjectLineItemAccessory.objects.all().select_related(
        'line_item', 'line_item__project', 'line_item__project__customer',
        'product_variant', 'product_variant__product', 'product_variant__product__brand',
        'product_variant__product__category'
    ).prefetch_related('product_variant__images')
    
    serializer_class = ProjectLineItemAccessorySerializer
    search_fields = [
        'product_variant__product__name', 
        'product_variant__color_name',
        'product_variant__material_code',
        'line_item__project__customer__name'
    ]
    ordering_fields = ['total_price', 'created_at', 'updated_at']
    
    def get_queryset(self):
        """Filter accessories by project or line item"""
        queryset = self.queryset
        
        project_id = self.request.query_params.get('project')
        line_item_id = self.request.query_params.get('line_item')
        category = self.request.query_params.get('category')
        
        if project_id:
            queryset = queryset.filter(line_item__project=project_id)
        
        if line_item_id:
            queryset = queryset.filter(line_item=line_item_id)
            
        if category:
            queryset = queryset.filter(product_variant__product__category__name__icontains=category)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def available_products(self, request):
        """Get available product variants for accessories"""
        from catalog.models import ProductVariant
        from catalog.serializers import ProductVariantSerializer
        
        # Get query parameters
        category_name = request.query_params.get('category', 'ACCESSORIES')
        search = request.query_params.get('search', '')
        brand_id = request.query_params.get('brand')
        
        # Base queryset - active product variants
        variants = ProductVariant.objects.filter(
            is_active=True,
            product__is_active=True
        ).select_related(
            'product', 'product__category', 'product__brand'
        ).prefetch_related('images')
        
        # Filter by category
        if category_name:
            variants = variants.filter(
                product__category__name__icontains=category_name
            )
        
        # Filter by brand
        if brand_id:
            variants = variants.filter(product__brand_id=brand_id)
        
        # Search filter
        if search:
            variants = variants.filter(
                Q(product__name__icontains=search) |
                Q(color_name__icontains=search) |
                Q(material_code__icontains=search) |
                Q(product__description__icontains=search)
            )
        
        # Pagination
        page = self.paginate_queryset(variants)
        if page is not None:
            serializer = ProductVariantSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get available categories for filtering"""
        from catalog.models import Category
        from catalog.serializers import CategorySerializer
        
        categories = Category.objects.filter(
            is_active=True,
            product__variants__is_active=True
        ).distinct()
        
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """Create accessory and recalculate totals"""
        accessory = serializer.save()
        
        # Auto-populate pricing from product variant if not provided
        if not accessory.unit_price:
            accessory.unit_price = accessory.product_variant.company_price
            accessory.tax_rate_snapshot = accessory.product_variant.tax_rate
            accessory.save()
        
        # Recalculate line item and project totals
        compute_line(accessory.line_item)
        recompute_totals(accessory.line_item.project)
    
    def perform_update(self, serializer):
        """Update accessory and recalculate totals"""
        accessory = serializer.save()
        compute_line(accessory.line_item)
        recompute_totals(accessory.line_item.project)
    
    def perform_destroy(self, instance):
        """Delete accessory and recalculate totals"""
        line_item = instance.line_item
        project = line_item.project
        super().perform_destroy(instance)
        compute_line(line_item)
        recompute_totals(project)

class ProjectTotalsViewSet(BaseModelViewSet):
    queryset = ProjectTotals.objects.all().select_related('project')
    serializer_class = ProjectTotalsSerializer
    http_method_names = ['get', 'head', 'options']  # Read-only

    def get_queryset(self):
        """Filter totals by project if provided"""
        project_id = self.request.query_params.get('project')
        if project_id:
            return self.queryset.filter(project=project_id)
        return self.queryset

class ProjectPlanImageGroupViewSet(BaseModelViewSet):
    queryset = ProjectPlanImageGroup.objects.all().prefetch_related('images')
    serializer_class = ProjectPlanImageGroupSerializer
    search_fields = ['title', 'description', 'project__customer__name']
    ordering_fields = ['sort_order', 'created_at', 'updated_at']
    
    def get_serializer_class(self):
        """Use different serializer for list view to optimize performance"""
        if self.action == 'list':
            return ProjectPlanImageGroupListSerializer
        return ProjectPlanImageGroupSerializer
    
    def get_queryset(self):
        """Filter groups by project if provided"""
        project_id = self.request.query_params.get('project')
        if project_id:
            return self.queryset.filter(project=project_id)
        return self.queryset
    
    @action(detail=True, methods=['post'])
    def reorder_images(self, request, pk=None):
        """Reorder images within a group"""
        group = self.get_object()
        image_orders = request.data.get('image_orders', [])
        
        try:
            with transaction.atomic():
                for order_data in image_orders:
                    image_id = order_data.get('id')
                    new_order = order_data.get('sort_order')
                    
                    if image_id and new_order is not None:
                        ProjectPlanImage.objects.filter(
                            id=image_id,
                            image_group=group
                        ).update(sort_order=new_order)
                
                return Response({'message': 'Images reordered successfully'})
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def reorder_groups(self, request):
        """Reorder groups within a project"""
        project_id = request.data.get('project')
        group_orders = request.data.get('group_orders', [])
        
        if not project_id:
            return Response(
                {'error': 'Project ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                for order_data in group_orders:
                    group_id = order_data.get('id')
                    new_order = order_data.get('sort_order')
                    
                    if group_id and new_order is not None:
                        ProjectPlanImageGroup.objects.filter(
                            id=group_id,
                            project=project_id
                        ).update(sort_order=new_order)
                
                return Response({'message': 'Groups reordered successfully'})
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class ProjectPlanImageViewSet(BaseModelViewSet):
    queryset = ProjectPlanImage.objects.all().select_related('image_group', 'image_group__project')
    serializer_class = ProjectPlanImageSerializer
    parser_classes = [MultiPartParser, FormParser]  # Support file uploads
    search_fields = ['caption', 'image_group__title', 'image_group__project__customer__name']
    ordering_fields = ['sort_order', 'created_at', 'updated_at']
    
    def get_queryset(self):
        """Filter images by group or project"""
        queryset = self.queryset
        
        project_id = self.request.query_params.get('project')
        group_id = self.request.query_params.get('image_group')
        
        if project_id:
            queryset = queryset.filter(image_group__project=project_id)
        
        if group_id:
            queryset = queryset.filter(image_group=group_id)
            
        return queryset
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Upload multiple images to a group at once"""
        image_group_id = request.data.get('image_group')
        
        if not image_group_id:
            return Response(
                {'error': 'image_group is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            image_group = get_object_or_404(ProjectPlanImageGroup, id=image_group_id)
        except:
            return Response(
                {'error': 'Image group not found'}, 
                status=status.HTTP_404
            )
        
        uploaded_images = []
        errors = []
        
        # Handle multiple file upload
        files = request.FILES.getlist('images')
        captions = request.POST.getlist('captions')
        
        try:
            with transaction.atomic():
                for i, file in enumerate(files):
                    try:
                        # Get caption for this image
                        caption = captions[i] if i < len(captions) else ''
                        
                        # Create image instance
                        image_data = {
                            'image_group': image_group.id,
                            'image': file,
                            'caption': caption,
                            'sort_order': len(uploaded_images)
                        }
                        
                        serializer = self.get_serializer(data=image_data)
                        if serializer.is_valid():
                            image = serializer.save()
                            uploaded_images.append(serializer.data)
                        else:
                            errors.append({
                                'file': file.name,
                                'errors': serializer.errors
                            })
                    
                    except Exception as e:
                        errors.append({
                            'file': file.name,
                            'error': str(e)
                        })
            
            return Response({
                'uploaded_images': uploaded_images,
                'errors': errors,
                'total_uploaded': len(uploaded_images),
                'total_errors': len(errors)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Reorder a specific image within its group"""
        image = self.get_object()
        new_order = request.data.get('sort_order')
        
        if new_order is None:
            return Response(
                {'error': 'sort_order is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            image.sort_order = new_order
            image.save()
            
            return Response({
                'message': 'Image reordered successfully',
                'data': self.get_serializer(image).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
# =========================
# Additional API Views
# =========================

class ProjectCalculationAPI(APIView):
    """API for project calculation utilities"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def post(self, request):
        """Calculate square footage for given dimensions"""
        try:
            cabinet_type_id = request.data.get('cabinet_type_id')
            width_mm = request.data.get('width_mm')
            depth_mm = request.data.get('depth_mm')
            height_mm = request.data.get('height_mm')
            
            if not all([cabinet_type_id, width_mm, depth_mm, height_mm]):
                return Response(
                    {'error': 'Missing required parameters'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cabinet_type = CabinetTypes.objects.get(id=cabinet_type_id)
            cab_sqft, door_sqft = compute_sqft(cabinet_type, width_mm, depth_mm, height_mm)
            
            return Response({
                'cabinet_sqft': str(cab_sqft),
                'door_sqft': str(door_sqft)
            })
            
        except CabinetTypes.DoesNotExist:
            return Response(
                {'error': 'Cabinet type not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActiveRatesAPI(APIView):
    """API to get active rates for a specific date"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request):
        """Get active rates for materials and brands"""
        eff_date_str = request.query_params.get('date', str(now().date()))
        
        try:
            eff_date = date.fromisoformat(eff_date_str)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get active finish rates
        finish_rates = _active_on(FinishRates.objects.all(), eff_date).select_related('material')
        door_rates = _active_on(DoorFinishRates.objects.all(), eff_date).select_related('material')
        brand_charges = _active_on(CabinetTypeBrandCharge.objects.all(), eff_date).select_related('cabinet_type')
        
        return Response({
            'date': eff_date,
            'finish_rates': FinishRatesSerializer(finish_rates, many=True).data,
            'door_rates': DoorFinishRatesSerializer(door_rates, many=True).data,
            'brand_charges': CabinetTypeBrandChargeSerializer(brand_charges, many=True).data
        })
    




# new 
class LightingRulesViewSet(BaseModelViewSet):
    queryset = LightingRules.objects.all().select_related(
        'cabinet_material', 'cabinet_type', 'customer'
    )
    serializer_class = LightingRulesSerializer
    search_fields = ['name', 'cabinet_material__name', 'cabinet_type__name', 'budget_tier']
    ordering_fields = ['led_strip_rate_per_mm', 'effective_from', 'name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by customer context
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(
                Q(is_global=True) | Q(customer_id=customer_id)
            )
        
        # Filter by material
        material_id = self.request.query_params.get('material')
        if material_id:
            queryset = queryset.filter(cabinet_material_id=material_id)
            
        # Filter by cabinet type
        cabinet_type_id = self.request.query_params.get('cabinet_type')
        if cabinet_type_id:
            queryset = queryset.filter(
                Q(cabinet_type_id=cabinet_type_id) | Q(cabinet_type__isnull=True)
            )
            
        # Filter by budget tier
        budget_tier = self.request.query_params.get('budget_tier')
        if budget_tier:
            queryset = queryset.filter(budget_tier=budget_tier)
        
        return queryset.order_by(
            # Customer-specific rules first
            Case(
                When(customer__isnull=False, then=Value(0)),
                default=Value(1)
            ),
            # Type-specific rules next
            Case(
                When(cabinet_type__isnull=False, then=Value(0)),
                default=Value(1)
            ),
            '-effective_from'
        )
    
    @action(detail=False, methods=['get'])
    def applicable_rules(self, request):
        """Get rules applicable to specific project context"""
        project_id = request.query_params.get('project')
        if not project_id:
            return Response({'error': 'Project ID required'}, status=400)
            
        try:
            project = Project.objects.get(id=project_id)
            
            # Get unique material/type combinations from project line items
            combinations = project.lines.values(
                'cabinet_material', 'cabinet_type',
                'cabinet_material__name', 'cabinet_type__name'
            ).distinct()
            
            result = []
            for combo in combinations:
                material_id = combo['cabinet_material']
                type_id = combo['cabinet_type']
                
                material = Materials.objects.get(id=material_id)
                cabinet_type = CabinetTypes.objects.get(id=type_id) if type_id else None
                
                rules = get_applicable_lighting_rules(project, material, cabinet_type)
                
                result.append({
                    'material': MaterialsSerializer(material).data,
                    'cabinet_type': CabinetTypesSerializer(cabinet_type).data if cabinet_type else None,
                    'applicable_rules': LightingRulesSerializer(rules, many=True).data
                })
            
            return Response(result)
            
        except Project.DoesNotExist:
            return Response({'error': 'Project not found'}, status=404)


class ProjectLightingConfigurationViewSet(BaseModelViewSet):
    queryset = ProjectLightingConfiguration.objects.all().select_related('project')
    serializer_class = ProjectLightingConfigurationSerializer
    http_method_names = ['get', 'put', 'patch', 'head', 'options']  # No create/delete
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def auto_create_items(self, request, pk=None):
        """Automatically create lighting items based on project line items"""
        config = self.get_object()
        
        with transaction.atomic():
            created_items = auto_create_lighting_items_for_project(config.project)
            
        return Response({
            'message': f'Created {len(created_items)} lighting items',
            'created_items': ProjectLightingItemSerializer(created_items, many=True).data
        })
    
    @action(detail=True, methods=['post'])
    def recalculate_totals(self, request, pk=None):
        """Recalculate all lighting totals for project"""
        config = self.get_object()
        
        with transaction.atomic():
            # Recalculate all lighting item costs
            for item in config.project.lighting_items.filter(is_active=True):
                item.calculate_costs()
                item.save()
            
            # Recalculate project totals
            calculate_project_lighting_totals(config.project)
            
        serializer = self.get_serializer(config)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get lighting cost summary by material/type"""
        config = self.get_object()
        
        items = config.project.lighting_items.filter(is_active=True)
        summary = []
        
        for item in items:
            summary.append({
                'material': item.cabinet_material.name,
                'cabinet_type': item.cabinet_type.name if item.cabinet_type else 'All Types',
                'led_cost': item.led_under_wall_cost + item.led_work_top_cost + item.led_skirting_cost,
                'spot_cost': item.spot_lights_cost,
                'total_cost': item.total_cost,
                'specifications': {
                    'led': item.lighting_rule.led_specification,
                    'spot': item.lighting_rule.spot_light_specification
                }
            })
        
        return Response({
            'items': summary,
            'grand_total': config.grand_total_lighting_cost,
            'total_led_cost': sum(item['led_cost'] for item in summary),
            'total_spot_cost': sum(item['spot_cost'] for item in summary)
        })



class ProjectLightingItemViewSet(BaseModelViewSet):
    queryset = ProjectLightingItem.objects.all().select_related(
        'project', 'lighting_rule', 'cabinet_material', 'cabinet_type'
    )
    serializer_class = ProjectLightingItemSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by active status
        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)
            
        return queryset
    
    def perform_create(self, serializer):
        # Automatically calculate costs on creation
        instance = serializer.save()
        instance.calculate_costs()
        instance.save()
        
        # Recalculate project totals
        calculate_project_lighting_totals(instance.project)
    
    def perform_update(self, serializer):
        # Automatically recalculate costs on update
        instance = serializer.save()
        instance.calculate_costs()
        instance.save()
        
        # Recalculate project totals
        calculate_project_lighting_totals(instance.project)
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Manually recalculate costs for this lighting item"""
        item = self.get_object()
        item.calculate_costs()
        item.save()
        
        # Recalculate project totals
        calculate_project_lighting_totals(item.project)
        
        serializer = self.get_serializer(item)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle active status of lighting item"""
        item = self.get_object()
        item.is_active = not item.is_active
        item.save()
        
        # Recalculate project totals
        calculate_project_lighting_totals(item.project)
        
        serializer = self.get_serializer(item)
        return Response(serializer.data)
    




def get_applicable_lighting_rules(project, cabinet_material=None, cabinet_type=None):
    """Get lighting rules applicable to a project"""
    rules = LightingRules.objects.filter(
        Q(is_global=True) | Q(customer=project.customer),
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
        Case(
            When(customer=project.customer, then=Value(0)),
            default=Value(1)
        ),
        Case(
            When(cabinet_type__isnull=False, then=Value(0)),
            default=Value(1)
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