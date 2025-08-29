from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'catalog' 

# API Router for ViewSets
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'brands', views.BrandViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'product-variants', views.ProductVariantViewSet)

urlpatterns = [
    # API (router)
    path('', include(router.urls)),

    # Dashboard and Statistics APIs
    path('dashboard/', views.CatalogDashboardAPIView.as_view(), name='catalog_dashboard'),
    path('search-suggestions/', views.ProductSearchSuggestionsAPIView.as_view(), name='search_suggestions'),
    path('price-analysis/', views.PriceAnalysisAPIView.as_view(), name='price_analysis'),
    path('inventory-report/', views.InventoryReportAPIView.as_view(), name='inventory_report'),

    # NEW: Price calculation endpoints
    path('calculate-price/', views.PriceCalculatorAPIView.as_view(), name='calculate_price'),
    path('utilities/', views.CatalogUtilitiesAPIView.as_view(), name='catalog_utilities'),
    
    # Category endpoints
    path('categories/<int:pk>/products/', views.CategoryViewSet.as_view({'get': 'products'}), name='category_products'),
    path('categories/<int:pk>/brands/', views.CategoryViewSet.as_view({'get': 'brands'}), name='category_brands'),

    # Brand endpoints
    path('brands/<int:pk>/products/', views.BrandViewSet.as_view({'get': 'products'}), name='brand_products'),

    # Product endpoints
    path('products/search/', views.ProductViewSet.as_view({'get': 'search'}), name='product_search'),
    path('products/<int:pk>/variants/', views.ProductViewSet.as_view({'get': 'variants'}), name='product_variants'),
    path('products/low-stock/', views.ProductViewSet.as_view({'get': 'low_stock'}), name='low_stock_products'),

    # Product Variant endpoints
    path('product-variants/calculate-price/', views.ProductVariantViewSet.as_view({'post': 'calculate_price'}), name='variant_calculate_price'),
    path('product-variants/<int:pk>/update-pricing/', views.ProductVariantViewSet.as_view({'post': 'update_pricing'}), name='update_variant_pricing'),
    path('product-variants/<int:pk>/price-breakdown/', views.ProductVariantViewSet.as_view({'get': 'price_breakdown'}), name='variant_price_breakdown'),
    path('product-variants/by-color/', views.ProductVariantViewSet.as_view({'get': 'by_color'}), name='variants_by_color'),
    path('product-variants/by-size-range/', views.ProductVariantViewSet.as_view({'get': 'by_size_range'}), name='variants_by_size_range'),
    path('product-variants/<int:pk>/update-stock/', views.ProductVariantViewSet.as_view({'post': 'update_stock'}), name='update_variant_stock'),

    # Traditional Django Views
    path('overview/', views.catalog_overview, name='overview'),
    path('products-list/', views.product_list_view, name='product_list'),
    path('products-detail/<int:product_id>/', views.product_detail_view, name='product_detail'),
]