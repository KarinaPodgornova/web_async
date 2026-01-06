from django.db import models
from django.contrib.auth.models import User


class Current(models.Model):
    """Модель заявки на расчет силы тока"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('processing', 'В обработке'),
        ('completed', 'Завершена'),
        ('rejected', 'Отклонена'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Название")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='currents', verbose_name="Создатель")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class Device(models.Model):
    """Модель устройства в заявке"""
    current = models.ForeignKey(Current, on_delete=models.CASCADE, related_name='devices', verbose_name="Заявка")
    device_name = models.CharField(max_length=200, verbose_name="Название устройства")
    device_power = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Мощность устройства (Вт)")
    amount = models.IntegerField(verbose_name="Количество")
    amperage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Сила тока (А)")
    
    class Meta:
        verbose_name = "Устройство"
        verbose_name_plural = "Устройства"
    
    def __str__(self):
        return f"{self.device_name} (x{self.amount})"
