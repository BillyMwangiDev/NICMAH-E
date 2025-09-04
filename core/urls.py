"""
Core URL configuration for Nichmah Agrovet.
"""

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health_check"),
]

# Robots.txt minimal include target
robots_urlpatterns = []