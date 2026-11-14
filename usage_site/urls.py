"""
urls.py

Root URL configuration for the usage dashboard project.
"""

from django.urls import include, path

urlpatterns = [
    path("", include("dashboard.urls")),
]
