"""
Core URL configuration for NICMAH.
"""

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health_check"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]

# Robots.txt minimal include target
robots_urlpatterns = []