from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterUserSerializer,
    UserDetailSerializer,
    ChangePasswordSerializer
)
from django.http import HttpResponse

def home_view(request):
    return HttpResponse("🎉 Welcome to Speisekamer Backend!")

# Custom permission to check if user is superadmin
class IsSuperAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'superadmin'

# Login View - Both staff and superadmin can login
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Get the user to check if they're active
            user = authenticate(
                username=request.data.get('username'),
                password=request.data.get('password')
            )
            
            if user and not user.is_active:
                return Response(
                    {"error": "This account has been deactivated. Please contact your administrator."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            response_data = serializer.validated_data
            response_data['message'] = f"Welcome {user.get_full_name() or user.username}!"
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

# Logout View - Any authenticated user can logout
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Logout successful"}, 
                status=status.HTTP_200_OK
            )
        except TokenError:
            # Token might already be blacklisted
            return Response(
                {"message": "Logout successful"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

# Register Staff View - Only superadmin can register new staff
class RegisterStaffView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": f"Staff member '{user.username}' created successfully!",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role
                    }
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# List all staff members - Only superadmin can view
class StaffListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        # Get all users except the requesting superadmin
        staff_members = CustomUser.objects.exclude(id=request.user.id).order_by('-date_joined')
        serializer = UserDetailSerializer(staff_members, many=True)
        
        return Response({
            "count": staff_members.count(),
            "results": serializer.data
        }, status=status.HTTP_200_OK)

# Get, Update, Delete specific staff member - Only superadmin can access
class StaffDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            serializer = UserDetailSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Prevent superadmin from editing their own role
            if user.id == request.user.id and 'role' in request.data:
                request.data.pop('role')
            
            serializer = UserDetailSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "User updated successfully",
                        "user": serializer.data
                    }, 
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Prevent superadmin from deleting themselves
            if user.id == request.user.id:
                return Response(
                    {"error": "You cannot delete your own account"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Soft delete - just deactivate the user
            user.is_active = False
            user.save()
            
            return Response(
                {"message": f"User '{user.username}' has been deactivated"}, 
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

# User Profile View - Any authenticated user can view their own profile
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Change Password View - Any authenticated user can change their password
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response(
                {"message": "Password changed successfully. Please login with your new password."}, 
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Dashboard View - Different content based on role
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if user.role == 'superadmin':
            # Superadmin dashboard data
            data = {
                "message": f"Welcome Super Admin {user.username}!",
                "role": user.role,
                "stats": {
                    "total_users": CustomUser.objects.count(),
                    "total_staff": CustomUser.objects.filter(role='staff').count(),
                    "active_staff": CustomUser.objects.filter(role='staff', is_active=True).count(),
                    "inactive_staff": CustomUser.objects.filter(role='staff', is_active=False).count(),
                },
                "capabilities": [
                    "Create new staff accounts",
                    "View all staff members",
                    "Edit staff information",
                    "Deactivate staff accounts",
                    "View system statistics"
                ]
            }
        else:
            # Staff dashboard data
            data = {
                "message": f"Welcome {user.get_full_name() or user.username}!",
                "role": user.role,
                "profile": {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.get_full_name(),
                    "date_joined": user.date_joined
                },
                "capabilities": [
                    "View your profile",
                    "Change your password",
                    "Access staff resources"
                ]
            }
        
        return Response(data, status=status.HTTP_200_OK)