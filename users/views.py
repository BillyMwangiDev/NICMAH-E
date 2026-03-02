"""
User authentication and profile views for NICMAH application.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from datetime import timedelta
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import UserProfile, SellerProfile
from pos.models import POSSale
from django.db import models


def login_view(request):
    """User login view with modern UI."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin:index")
        else:
            return redirect("core:home")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")

                # Redirect based on user role
                if user.is_staff:
                    return redirect("admin:index")  # Django admin
                elif user.role == "manager":
                    return redirect("pos:dashboard")
                elif user.role == "seller":
                    return redirect("users:seller_dashboard")
                else:
                    return redirect("users:dashboard")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AuthenticationForm()

    context = {"form": form, "page_title": "Login", "show_sidebar": False}
    return render(request, "users/login.html", context)


def signup_view(request):
    """User registration view with modern UI."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created successfully! Welcome to {user.first_name or user.username}!")
            return redirect("core:home")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()

    context = {"form": form, "page_title": "Sign Up", "show_sidebar": False}
    return render(request, "users/signup.html", context)


def logout_view(request):
    """User logout view."""
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect("core:home")


@login_required
def profile_view(request):
    """User profile view."""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        user_form = CustomUserChangeForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("users:profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = CustomUserChangeForm(instance=request.user)

    context = {"user_form": user_form, "profile": profile, "page_title": "My Profile"}
    return render(request, "users/profile.html", context)


@login_required
def dashboard_view(request):
    """User dashboard view based on role."""
    user = request.user

    if user.is_staff:
        # Admin dashboard
        context = {"page_title": "Admin Dashboard", "user": user, "is_admin": True}
        return render(request, "users/admin_dashboard.html", context)
    elif user.role == "manager":
        # Manager dashboard
        return redirect("pos:dashboard")
    elif user.role == "seller":
        # Seller dashboard
        return redirect("users:seller_dashboard")
    else:
        # Customer dashboard
        context = {"page_title": "My Dashboard", "user": user, "is_customer": True}
        return render(request, "users/customer_dashboard.html", context)


@login_required
def seller_dashboard_view(request):
    """Seller dashboard view with performance metrics."""
    user = request.user

    # Ensure user is a seller
    if user.role != "seller":
        messages.error(request, "Access denied. Seller role required.")
        return redirect("users:dashboard")

    # Get or create seller profile
    try:
        seller_profile = user.sellerprofile
    except SellerProfile.DoesNotExist:
        seller_profile = SellerProfile.objects.create(user=user)

    # Get recent sales (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sales = POSSale.objects.filter(seller=user, created_at__gte=thirty_days_ago, status="completed").order_by(
        "-created_at"
    )[:10]

    # Prepare chart data for last 30 days
    sales_chart_labels = []
    sales_chart_data = []

    for i in range(30):
        date = timezone.now() - timedelta(days=29 - i)
        day_sales = (
            POSSale.objects.filter(seller=user, created_at__date=date.date(), status="completed").aggregate(
                total=models.Sum("total_amount")
            )["total"]
            or 0
        )

        sales_chart_labels.append(date.strftime("%b %d"))
        sales_chart_data.append(float(day_sales))

    # Calculate commission earned
    commission_earned = seller_profile.get_commission_earned()

    context = {
        "page_title": "Seller Dashboard",
        "user": user,
        "seller_profile": seller_profile,
        "recent_sales": recent_sales,
        "sales_chart_labels": sales_chart_labels,
        "sales_chart_data": sales_chart_data,
        "commission_earned": commission_earned,
        "total_sales": seller_profile.total_sales,
    }

    return render(request, "users/seller_dashboard.html", context)
