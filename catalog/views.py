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
    """ViewSet for managing product variants"""

    queryset = ProductVariant.objects.select_related('product', 'size', 'color').prefetch_related('images', 'detailed_specs')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'product__category', 'product__brand', 'is_active']
    search_fields = ['material_code', 'sku_code', 'product__name']
    ordering_fields = ['value', 'stock_quantity', 'created_at']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductVariantListSerializer
        return ProductVariantSerializer

    def get_queryset(self):
        queryset = ProductVariant.objects.select_related(
            'product', 'product__category', 'product__brand', 'size', 'color'
        ).prefetch_related('images', 'detailed_specs')

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
            queryset = queryset.filter(value__gte=min_price)
        if max_price:
            queryset = queryset.filter(value__lte=max_price)

        return queryset

    def perform_update(self, serializer):
        """Track price changes when updating"""
        track_price_fields = {'mrp', 'discount_percentage'}
        incoming_fields = set(self.request.data.keys())
        old_instance = self.get_object()

        instance = serializer.save()

        # Create price history record if values changed
        if track_price_fields & incoming_fields:
            if (old_instance.mrp != instance.mrp or
                    old_instance.discount_percentage != instance.discount_percentage):
                ProductPriceHistory.objects.create(
                    product_variant=instance,
                    old_mrp=old_instance.mrp,
                    new_mrp=instance.mrp,
                    old_discount=old_instance.discount_percentage,
                    new_discount=instance.discount_percentage,
                    changed_by=self.request.user if self.request.user.is_authenticated else None,
                    reason=self.request.data.get('price_change_reason', 'Updated via API')
                )
    
    @action(detail=True, methods=['post'], url_path='upload-images')
    def upload_images(self, request, pk=None):
        variant = self.get_object()
        files = request.FILES.getlist('images') or ([request.FILES['image']] if 'image' in request.FILES else [])
        if not files:
            return Response({'detail': "No images provided. Use 'images'[] or 'image'."}, status=400)

        created = []
        for idx, f in enumerate(files):
            created.append(ProductImage.objects.create(
                product_variant=variant,
                image=f,
                alt_text=request.data.get('alt_text', ''),
                is_primary=str(request.data.get('is_primary', '')).lower() in ('1', 'true', 'yes') and idx == 0,
                sort_order=int(request.data.get('sort_order', 0)),
            ))
        return Response(ProductImageSerializer(created, many=True, context=self.get_serializer_context()).data, status=201)

    @action(detail=True, methods=['get'], url_path='images')
    def list_images(self, request, pk=None):
        variant = self.get_object()
        qs = variant.images.order_by('sort_order', 'id')
        return Response(ProductImageSerializer(qs, many=True, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """Update stock quantity"""
        variant = self.get_object()
        new_quantity = request.data.get('stock_quantity')

        if new_quantity is None:
            return Response({'error': 'stock_quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_quantity = int(new_quantity)
            if new_quantity < 0:
                return Response({'error': 'Stock quantity cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid stock quantity'}, status=status.HTTP_400_BAD_REQUEST)

        variant.stock_quantity = new_quantity
        variant.save(update_fields=['stock_quantity'])

        return Response({
            'message': 'Stock updated successfully',
            'new_stock': variant.stock_quantity
        })

    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        """Get price change history for this variant"""
        variant = self.get_object()
        history = variant.price_history.all()

        serializer = ProductPriceHistorySerializer(history, many=True)
        return Response(serializer.data)



# ============================================================================
# Dashboard and Statistics Views
# ============================================================================

# @require_http_methods(["GET"])
# def catalog_dashboard(request):
    

class CatalogDashboardAPIView(APIView):
    """Dashboard API view with proper DRF authentication"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Basic statistics
        total_products = Product.objects.filter(is_active=True).count()
        total_variants = ProductVariant.objects.filter(is_active=True).count()
        total_categories = Category.objects.filter(is_active=True).count()
        total_brands = Brand.objects.filter(is_active=True).count()

        # Stock statistics
        low_stock_count = ProductVariant.objects.filter(
            is_active=True,
            stock_quantity__lte=10,
            stock_quantity__gt=0
        ).count()

        out_of_stock_count = ProductVariant.objects.filter(
            is_active=True,
            stock_quantity=0
        ).count()

        # Value statistics
        total_value = ProductVariant.objects.filter(is_active=True).aggregate(
            total=Sum('value')
        )['total'] or Decimal('0.00')

        # Category breakdown
        category_stats = Category.objects.filter(is_active=True).annotate(
            product_count=Count('product', filter=Q(product__is_active=True))
        ).values('id', 'name', 'product_count')

        # Brand breakdown
        brand_stats = Brand.objects.filter(is_active=True).annotate(
            product_count=Count('product', filter=Q(product__is_active=True))
        ).values('id', 'name', 'product_count')

        data = {
            'total_products': total_products,
            'total_variants': total_variants,
            'total_categories': total_categories,
            'total_brands': total_brands,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'total_value': str(total_value),
            'category_breakdown': list(category_stats),
            'brand_breakdown': list(brand_stats)
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






