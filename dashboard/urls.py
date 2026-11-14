"""
urls.py

URL routes for the dashboard app.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("refresh/", views.refresh, name="refresh"),
]
