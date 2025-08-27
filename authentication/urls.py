from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    home_view,
    CustomTokenObtainPairView,
    LogoutView,
    RegisterStaffView,
    StaffListView,
    StaffDetailView,
    UserProfileView,
    ChangePasswordView,
    DashboardView,
)

urlpatterns = [
    # Home
    path('', home_view, name='home'),
    
    # Authentication endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Staff management endpoints (superadmin only)
    path('staff/register/', RegisterStaffView.as_view(), name='register_staff'),
    path('staff/', StaffListView.as_view(), name='staff_list'),
    path('staff/<int:user_id>/', StaffDetailView.as_view(), name='staff_detail'),
    
    # User endpoints (authenticated users)
    path('api/user/profile/', UserProfileView.as_view(), name='user_profile'),
    path('api/user/change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Dashboard
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
]