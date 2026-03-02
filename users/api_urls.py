"""
API URL configuration for JWT authentication endpoints.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from .api_views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenBlacklistView,
    logout_view,
    user_profile,
)

app_name = 'users_api'

urlpatterns = [
    # JWT Authentication endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/blacklist/', CustomTokenBlacklistView.as_view(), name='token_blacklist'),
    
    # User endpoints
    path('logout/', logout_view, name='logout'),
    path('profile/', user_profile, name='user_profile'),
]
