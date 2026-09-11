"""
URL configuration for tracker project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', include('expenses.urls_auth')),
    path('', include('expenses.urls')),
]
