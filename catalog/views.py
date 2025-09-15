from decimal import Decimal
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg, Min, Max, F
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from decimal import Decimal
import io
from reportlab.lib.pagesizes import A4
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils.timezone import now

from .models import *
from .serializers import *

from rest_framework.views import APIView

class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing product categories"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']

    def get_queryset(self):
        queryset = Category.objects.all()

        # Filter by active status
        is_active = self.request.query_params.get('active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get products in this category"""
        category = self.get_object()
        products = Product.objects.filter(category=category, is_active=True)

        # Apply pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def brands(self, request, pk=None):
        """Get brands available in this category"""
        category = self.get_object()
        # CategoryBrand reverse query name from Brand is "categorybrand"
        brands = Brand.objects.filter(
            categorybrand__category=category,
            is_active=True
        ).distinct()

        serializer = BrandSerializer(brands, many=True, context={'request': request})
        return Response(serializer.data)


class BrandViewSet(viewsets.ModelViewSet):
    """ViewSet for managing brands"""

    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get products from this brand"""
        brand = self.get_object()
        products = Product.objects.filter(brand=brand, is_active=True)

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet for managing products"""

    queryset = Product.objects.select_related('category', 'brand').prefetch_related('variants')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_active']
    search_fields = ['name', 'description', 'brand__name', 'category__name']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'brand').prefetch_related('variants')

        # Filter by active status
        is_active = self.request.query_params.get('active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    @action(detail=True, methods=['get'])
    def variants(self, request, pk=None):
        """Get all variants for this product"""
        product = self.get_object()
        variants = product.variants.filter(is_active=True).select_related('size', 'color')

        serializer = ProductVariantListSerializer(variants, many=True, context={'request': request})
        return Response(serializer.data)


    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get variants with low stock"""
        threshold = int(request.query_params.get('threshold', 10))
        variants = ProductVariant.objects.filter(
            stock_quantity__lte=threshold,
            stock_quantity__gt=0,
            is_active=True
        ).select_related('product', 'size', 'color')

        serializer = ProductVariantListSerializer(variants, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced product search"""
        serializer = ProductSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset()

        # Apply search filters
        query = serializer.validated_data.get('query')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(brand__name__icontains=query) |
                Q(variants__material_code__icontains=query)
            ).distinct()

        category = serializer.validated_data.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        brand = serializer.validated_data.get('brand')
        if brand:
            queryset = queryset.filter(brand_id=brand)

        # Price filtering (based on variants)
        min_price = serializer.validated_data.get('min_price')
        max_price = serializer.validated_data.get('max_price')
        if min_price or max_price:
            price_filter = Q()
            if min_price is not None:
                price_filter &= Q(variants__value__gte=min_price)
            if max_price is not None:
                price_filter &= Q(variants__value__lte=max_price)
            queryset = queryset.filter(price_filter).distinct()

        # Stock filtering
        in_stock = serializer.validated_data.get('in_stock')
        if in_stock:
            queryset = queryset.filter(variants__stock_quantity__gt=0).distinct()

        page = self.paginate_queryset(queryset)
        if page is not None:
            response_serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(response_serializer.data)

        response_serializer = ProductListSerializer(queryset, many=True, context={'request': request})
        return Response(response_serializer.data)


class ProductVariantViewSet(viewsets.ModelViewSet):
    """Updated ViewSet for managing product variants with price calculations"""

    queryset = ProductVariant.objects.select_related(
        'product', 'product__category', 'product__brand'
    ).prefetch_related('images')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'product__category', 'product__brand', 'is_active']
    search_fields = ['material_code', 'sku_code', 'product__name', 'color_name']
    ordering_fields = ['company_price', 'stock_quantity', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductVariantListSerializer
        return ProductVariantSerializer

    def get_queryset(self):
        queryset = ProductVariant.objects.select_related(
            'product', 'product__category', 'product__brand'
        ).prefetch_related('images')

        # Filter by stock status
        stock_status = self.request.query_params.get('stock_status', None)
        if stock_status == 'in_stock':
            queryset = queryset.filter(stock_quantity__gt=0)
        elif stock_status == 'low_stock':
            queryset = queryset.filter(stock_quantity__lte=10, stock_quantity__gt=0)
        elif stock_status == 'out_of_stock':
            queryset = queryset.filter(stock_quantity=0)

        # Price range filtering
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(company_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(company_price__lte=max_price)

        # Color filtering
        color = self.request.query_params.get('color')
        if color:
            queryset = queryset.filter(color_name__icontains=color)

        return queryset

    @action(detail=False, methods=['post'])
    def calculate_price(self, request):
        """Calculate price breakdown without saving"""
        serializer = PriceCalculationSerializer(data=request.data)
        if serializer.is_valid():
            return Response({
                'message': 'Price calculated successfully',
                'calculations': serializer.validated_data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_pricing(self, request, pk=None):
        """Update variant pricing with automatic recalculation"""
        variant = self.get_object()
        
        # Extract pricing fields from request
        pricing_fields = {}
        if 'mrp' in request.data:
            pricing_fields['mrp'] = request.data['mrp']
        if 'tax_rate' in request.data:
            pricing_fields['tax_rate'] = request.data['tax_rate']
        if 'discount_rate' in request.data:
            pricing_fields['discount_rate'] = request.data['discount_rate']
        
        if not pricing_fields:
            return Response(
                {'error': 'At least one pricing field (mrp, tax_rate, discount_rate) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate the data
        serializer = self.get_serializer(variant, data=pricing_fields, partial=True)
        if serializer.is_valid():
            updated_variant = serializer.save()
            return Response({
                'message': 'Pricing updated successfully',
                'variant': ProductVariantSerializer(updated_variant, context={'request': request}).data,
                'price_breakdown': updated_variant.price_breakdown
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def price_breakdown(self, request, pk=None):
        """Get detailed price breakdown for a variant"""
        variant = self.get_object()
        return Response({
            'variant_id': variant.id,
            'material_code': variant.material_code,
            'price_breakdown': variant.price_breakdown,
            'dimensions': variant.dimensions_display
        })

    @action(detail=False, methods=['get'])
    def by_color(self, request):
        """Get variants filtered by color"""
        color = request.query_params.get('color')
        if not color:
            return Response({'error': 'Color parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        variants = self.get_queryset().filter(color_name__icontains=color)
        serializer = ProductVariantListSerializer(variants, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_size_range(self, request):
        """Get variants within size range"""
        min_width = request.query_params.get('min_width')
        max_width = request.query_params.get('max_width')
        min_height = request.query_params.get('min_height')
        max_height = request.query_params.get('max_height')
        
        queryset = self.get_queryset()
        
        if min_width:
            queryset = queryset.filter(size_width__gte=min_width)
        if max_width:
            queryset = queryset.filter(size_width__lte=max_width)
        if min_height:
            queryset = queryset.filter(size_height__gte=min_height)
        if max_height:
            queryset = queryset.filter(size_height__lte=max_height)
        
        serializer = ProductVariantListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    

class PriceCalculatorAPIView(APIView):
    """Updated price calculator API without tax calculations"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Calculate price breakdown for given MRP and discount"""
        serializer = PriceCalculationSerializer(data=request.data)
        if serializer.is_valid():
            calculations = serializer.validated_data
            
            return Response({
                'success': True,
                'inputs': {
                    'mrp': str(calculations['mrp']),
                    'discount_rate': str(calculations['discount_rate'])
                },
                'calculations': {
                    'discount_amount': str(calculations['discount_amount']),
                    'company_price': str(calculations['company_price']),
                    'savings': str(calculations['savings'])
                },
                'breakdown': {
                    'mrp': f"₹{calculations['mrp']:,.2f}",
                    'discount': f"-₹{calculations['discount_amount']:,.2f} ({calculations['discount_rate']}%)",
                    'final_price': f"₹{calculations['company_price']:,.2f}",
                    'you_save': f"₹{calculations['savings']:,.2f}"
                }
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    

class CatalogUtilitiesAPIView(APIView):
    """Utilities for catalog management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get available colors and size ranges"""
        # Get unique colors
        colors = ProductVariant.objects.filter(
            is_active=True
        ).values_list('color_name', flat=True).distinct().order_by('color_name')
        
        # Get size ranges
        size_stats = ProductVariant.objects.filter(is_active=True).aggregate(
            min_width=models.Min('size_width'),
            max_width=models.Max('size_width'),
            min_height=models.Min('size_height'),
            max_height=models.Max('size_height'),
            min_depth=models.Min('size_depth'),
            max_depth=models.Max('size_depth')
        )
        
        return Response({
            'available_colors': list(colors),
            'size_ranges': size_stats,
            'tax_rate_options': [18.0, 12.0, 5.0, 0.0],  # Common tax rates
            'common_discount_rates': [0, 5, 10, 15, 20, 25, 30]  # Common discount rates
        })

    @action(detail=False, methods=['post'])
    def bulk_update_tax(self, request):
        """Bulk update tax rate for multiple variants"""
        variant_ids = request.data.get('variant_ids', [])
        new_tax_rate = request.data.get('tax_rate')
        
        if not variant_ids or new_tax_rate is None:
            return Response(
                {'error': 'variant_ids and tax_rate are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_tax_rate = Decimal(str(new_tax_rate))
            if new_tax_rate < 0 or new_tax_rate > 100:
                raise ValueError("Tax rate must be between 0 and 100")
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid tax rate'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update variants
        updated_count = 0
        for variant_id in variant_ids:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_active=True)
                variant.tax_rate = new_tax_rate
                variant.save()  # This will trigger recalculation
                updated_count += 1
            except ProductVariant.DoesNotExist:
                continue
        
        return Response({
            'message': f'Updated tax rate for {updated_count} variants',
            'updated_count': updated_count,
            'new_tax_rate': str(new_tax_rate)
        })

# ============================================================================
# Dashboard and Statistics Views
# ============================================================================

# @require_http_methods(["GET"])
# def catalog_dashboard(request):
    

class CatalogDashboardAPIView(APIView):
    """Updated Dashboard API view without tax and stock references"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Basic statistics
        total_products = Product.objects.filter(is_active=True).count()
        total_variants = ProductVariant.objects.filter(is_active=True).count()
        total_categories = Category.objects.filter(is_active=True).count()
        total_brands = Brand.objects.filter(is_active=True).count()

        # Value statistics (no more stock calculations)
        total_mrp = ProductVariant.objects.filter(is_active=True).aggregate(
            total=Sum('mrp')
        )['total'] or Decimal('0.00')

        total_discount_amount = ProductVariant.objects.filter(is_active=True).aggregate(
            total=Sum('discount_amount')
        )['total'] or Decimal('0.00')

        total_company_price = ProductVariant.objects.filter(is_active=True).aggregate(
            total=Sum('company_price')
        )['total'] or Decimal('0.00')

        # Category breakdown
        category_stats = Category.objects.filter(is_active=True).annotate(
            product_count=Count('product', filter=Q(product__is_active=True)),
            variant_count=Count('product__variants', filter=Q(product__variants__is_active=True)),
            total_mrp=Sum('product__variants__mrp', filter=Q(product__variants__is_active=True)),
            total_company_price=Sum('product__variants__company_price', filter=Q(product__variants__is_active=True))
        ).values('id', 'name', 'product_count', 'variant_count', 'total_mrp', 'total_company_price')

        # Brand breakdown
        brand_stats = Brand.objects.filter(is_active=True).annotate(
            product_count=Count('product', filter=Q(product__is_active=True)),
            variant_count=Count('product__variants', filter=Q(product__variants__is_active=True)),
            total_mrp=Sum('product__variants__mrp', filter=Q(product__variants__is_active=True)),
            total_company_price=Sum('product__variants__company_price', filter=Q(product__variants__is_active=True))
        ).values('id', 'name', 'product_count', 'variant_count', 'total_mrp', 'total_company_price')

        # Top performing variants by company price
        top_variants = ProductVariant.objects.filter(is_active=True).select_related('product').order_by('-company_price')[:10]

        top_variants_data = []
        for variant in top_variants:
            top_variants_data.append({
                'id': variant.id,
                'material_code': variant.material_code,
                'product_name': variant.product.name,
                'mrp': str(variant.mrp),
                'discount_rate': str(variant.discount_rate),
                'company_price': str(variant.company_price),
                'savings': str(variant.discount_amount),
                'dimensions': f"W:{variant.size_width or 0} × H:{variant.size_height or 0} × D:{variant.size_depth or 0}mm"
            })

        # Price range analysis based on company_price
        price_ranges = [
            {
                'range': '0-5000',
                'count': ProductVariant.objects.filter(
                    is_active=True, 
                    company_price__lt=5000
                ).count()
            },
            {
                'range': '5000-15000', 
                'count': ProductVariant.objects.filter(
                    is_active=True,
                    company_price__gte=5000, 
                    company_price__lt=15000
                ).count()
            },
            {
                'range': '15000-30000',
                'count': ProductVariant.objects.filter(
                    is_active=True,
                    company_price__gte=15000, 
                    company_price__lt=30000
                ).count()
            },
            {
                'range': '30000+',
                'count': ProductVariant.objects.filter(
                    is_active=True,
                    company_price__gte=30000
                ).count()
            }
        ]

        data = {
            # Basic counts
            'total_products': total_products,
            'total_variants': total_variants,
            'total_categories': total_categories,
            'total_brands': total_brands,
            
            # Financial statistics (no stock)
            'total_mrp': str(total_mrp),
            'total_discount_amount': str(total_discount_amount),
            'total_company_price': str(total_company_price),
            'total_savings': str(total_discount_amount),  # Total savings for customers
            
            # Breakdowns
            'category_breakdown': list(category_stats),
            'brand_breakdown': list(brand_stats),
            'price_ranges': price_ranges,
            
            # Top performers
            'top_variants': top_variants_data
        }

        return Response(data)


class ProductSearchSuggestionsAPIView(APIView):
    """Search suggestions API view"""
    # No authentication required for search suggestions
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'suggestions': []})

        # Product name suggestions
        products = Product.objects.filter(
            name__icontains=query,
            is_active=True
        )[:5].values('id', 'name')

        # Brand suggestions
        brands = Brand.objects.filter(
            name__icontains=query,
            is_active=True
        )[:3].values('id', 'name')

        # Material code suggestions
        variants = ProductVariant.objects.filter(
            material_code__icontains=query,
            is_active=True
        )[:5].values('id', 'material_code', 'product__name')

        suggestions = {
            'products': list(products),
            'brands': list(brands),
            'material_codes': list(variants)
        }

        return Response({'suggestions': suggestions})

class PriceAnalysisAPIView(APIView):
    """Price analysis API view"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        category_id = request.query_params.get('category')
        brand_id = request.query_params.get('brand')

        queryset = ProductVariant.objects.filter(is_active=True)

        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        if brand_id:
            queryset = queryset.filter(product__brand_id=brand_id)

        price_stats = queryset.aggregate(
            min_price=Min('value'),
            max_price=Max('value'),
            avg_price=Avg('value'),
            total_variants=Count('id')
        )

        # Price distribution
        price_ranges = [
            {'range': '0-1000', 'count': queryset.filter(value__lt=1000).count()},
            {'range': '1000-5000', 'count': queryset.filter(value__gte=1000, value__lt=5000).count()},
            {'range': '5000-10000', 'count': queryset.filter(value__gte=5000, value__lt=10000).count()},
            {'range': '10000+', 'count': queryset.filter(value__gte=10000).count()},
        ]

        # Cast decimals to string for safe JSON serialization
        for key in ('min_price', 'max_price', 'avg_price'):
            if isinstance(price_stats.get(key), Decimal):
                price_stats[key] = str(price_stats[key])

        return Response({
            'price_stats': price_stats,
            'price_distribution': price_ranges
        })


class InventoryReportAPIView(APIView):
    """Inventory report API view"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Stock status summary
        stock_summary = {
            'in_stock': ProductVariant.objects.filter(is_active=True, stock_quantity__gt=10).count(),
            'low_stock': ProductVariant.objects.filter(is_active=True, stock_quantity__lte=10, stock_quantity__gt=0).count(),
            'out_of_stock': ProductVariant.objects.filter(is_active=True, stock_quantity=0).count(),
        }

        # Top products by stock value
        top_value_products = ProductVariant.objects.filter(
            is_active=True,
            stock_quantity__gt=0
        ).annotate(
            stock_value=F('stock_quantity') * F('value')
        ).order_by('-stock_value')[:10].values(
            'product__name', 'material_code', 'stock_quantity', 'value', 'stock_value'
        )

        # Category-wise stock distribution
        category_stock = Category.objects.filter(is_active=True).annotate(
            total_stock=Sum('product__variants__stock_quantity', filter=Q(product__variants__is_active=True)),
            total_value=Sum(
                F('product__variants__stock_quantity') * F('product__variants__value'),
                filter=Q(product__variants__is_active=True)
            )
        ).values('name', 'total_stock', 'total_value')

        return Response({
            'stock_summary': stock_summary,
            'top_value_products': list(top_value_products),
            'category_distribution': list(category_stock)
        })


# ============================================================================
# Traditional Django Views (for admin interface)
# ============================================================================

@login_required
def catalog_overview(request):
    """Overview page for catalog management"""
    context = {
        'total_products': Product.objects.filter(is_active=True).count(),
        'total_variants': ProductVariant.objects.filter(is_active=True).count(),
        'low_stock_items': ProductVariant.objects.filter(
            is_active=True, stock_quantity__lte=10, stock_quantity__gt=0
        ).count(),
        'categories': Category.objects.filter(is_active=True).count(),
        'brands': Brand.objects.filter(is_active=True).count(),
    }
    return render(request, 'catalog/overview.html', context)


@login_required
def product_list_view(request):
    """List view for products with filtering"""
    products = Product.objects.select_related('category', 'brand').filter(is_active=True)

    # Apply filters
    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category_id=category_filter)

    brand_filter = request.GET.get('brand')
    if brand_filter:
        products = products.filter(brand_id=brand_filter)

    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'brands': Brand.objects.filter(is_active=True),
        'current_category': category_filter,
        'current_brand': brand_filter,
        'search_query': search_query,
    }

    return render(request, 'catalog/product_list.html', context)


@login_required
def product_detail_view(request, product_id):
    """Detail view for a specific product"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand'),
        id=product_id
    )

    variants = product.variants.filter(is_active=True).select_related('size', 'color')

    context = {
        'product': product,
        'variants': variants,
    }

    return render(request, 'catalog/product_detail.html', context)






