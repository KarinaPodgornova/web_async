from django.urls import path
from . import views

urlpatterns = [
    path('api/v1/calculate-current/', views.calculate_current, name='calculate-current'),
    path('api/v1/calculate-current-batch/', views.calculate_current_batch, name='calculate-current-batch'),
    path('api/health/', views.health_check, name='health-check'),
]