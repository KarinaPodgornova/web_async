from django.urls import path
from . import views

urlpatterns = [
    path('api/v1/calculate-current/', views.calculate_current, name='calculate-current'),
    path('api/v1/calculate-single-device/', views.calculate_single_device, name='calculate-single-device'),  # Изменили здесь
    path('api/v1/test-calculate/', views.test_calculation, name='test-calculate'),
    path('api/health/', views.health_check, name='health-check'),
]