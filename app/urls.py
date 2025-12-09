from django.urls import path
from . import views

urlpatterns = [
    # Используйте ТОЛЬКО реальные функции из views.py:
    
    # 1. Расчет одного устройства
    path('api/v1/calculate-single-device/', views.calculate_single_device, name='calculate-single-device'),
    
    # 2. Расчет всей заявки
    path('api/v1/calculate-entire-current/', views.calculate_entire_current, name='calculate-entire-current'),
    
    # 3. Health check
    path('api/health/', views.health_check, name='health-check'),
]