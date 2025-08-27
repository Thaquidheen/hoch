# pricing/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'pricing'

# API Router for Pricing ViewSets
router = DefaultRouter()

# Masters & Materials
router.register(r'categories', views.CategoryViewSet)
router.register(r'materials', views.MaterialsViewSet)
router.register(r'brands', views.BrandViewSet)
router.register(r'customers', views.CustomerViewSet)
router.register(r'accessories', views.AccessoriesViewSet)

# Rates & Pricing
router.register(r'finish-rates', views.FinishRatesViewSet)
router.register(r'door-finish-rates', views.DoorFinishRatesViewSet)

# Cabinet Configuration
router.register(r'cabinet-types', views.CabinetTypesViewSet)
router.register(r'cabinet-type-brand-charges', views.CabinetTypeBrandChargeViewSet)
router.register(r'geometry-rules', views.GeometryRuleViewSet)

# Project Management
router.register(r'projects', views.ProjectViewSet)
router.register(r'project-line-items', views.ProjectLineItemViewSet)
router.register(r'project-line-item-accessories', views.ProjectLineItemAccessoryViewSet)
router.register(r'project-totals', views.ProjectTotalsViewSet)
router.register(r'project-plan-images', views.ProjectPlanImageViewSet)

# Enhanced Lighting Configuration (UPDATED)
router.register(r'lighting-rules', views.LightingRulesViewSet)
router.register(r'lighting-configurations', views.ProjectLightingConfigurationViewSet)
router.register(r'lighting-items', views.ProjectLightingItemViewSet)

urlpatterns = [
    # Router URLs (provides full CRUD for all registered ViewSets)
    path('', include(router.urls)),
    
    # Custom API Views
    path('calculate/', views.ProjectCalculationAPI.as_view(), name='project_calculation'),
    path('active-rates/', views.ActiveRatesAPI.as_view(), name='active_rates'),
    
    # Custom ViewSet actions (if you need specific non-CRUD endpoints)
    # Example: GET list of hardware charges in matrix format
    path('hardware-charges/matrix/', views.CabinetTypeBrandChargeViewSet.as_view({'get': 'list'}), name='hardware_charges_matrix'),
]