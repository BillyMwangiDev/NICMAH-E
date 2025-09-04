"""
URL configuration for users app.
"""

from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("seller-dashboard/", views.seller_dashboard_view, name="seller_dashboard"),
]
