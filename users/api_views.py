"""
API views for user authentication using JWT tokens.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from django.contrib.auth import authenticate
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view that updates last_login and provides additional user info.
    """
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Update user's last_login
            user = authenticate(
                username=request.data.get('username') or request.data.get('email'),
                password=request.data.get('password')
            )
            if user:
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Add user info to response
                response.data['user'] = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
        
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view with rotation support.
    Token rotation is handled automatically by SIMPLE_JWT settings.
    """
    pass


class CustomTokenBlacklistView(TokenBlacklistView):
    """
    Custom token blacklist view for logout functionality.
    """
    pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint that blacklists the current refresh token.
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {'message': 'Successfully logged out'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get current user profile information.
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': user.phone_number,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
        'last_login': user.last_login,
    })
