from django.urls import path

from . import views

urlpatterns = [
    path("auth/token", views.token, name="auth-token"),
    path("auth/me", views.me, name="auth-me"),
    path("health", views.health, name="health"),
]
