from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import time
import random
import requests
import math
from concurrent import futures

# ======= 🔥 НАСТРОЙТЕ ПОД ВАШ СЕРВЕР =======
GO_SERVER_URL = "http://localhost/api/v1"  # Ваш Go сервер (порт 80)
AUTH_TOKEN = "secret123"
executor = futures.ThreadPoolExecutor(max_workers=5)
# =========================================

# ------------------- Функция расчета силы тока -------------------
def calculate_device_amperage(device_data, voltage_bord, amount):
    """
    Расчет силы тока для одного типа устройств
    Формула: I = √(P_ном / R_ном) * (K_запаса / (K_пд * (U_борт / U_ном))) * количество
    """
    try:
        # Проверка параметров
        if (device_data['power_nominal'] <= 0 or 
            device_data['resistance'] <= 0 or 
            device_data['voltage_nominal'] <= 0 or
            voltage_bord <= 0 or
            device_data['coeff_reserve'] <= 0 or
            device_data['coeff_efficiency'] <= 0):
            return 0, False, "Неверные параметры для расчёта тока"
        
        # 1. Вычисляем √(P_ном / R_ном)
        part1 = math.sqrt(device_data['power_nominal'] / device_data['resistance'])
        
        # 2. Вычисляем (U_борт / U_ном)
        voltage_ratio = voltage_bord / device_data['voltage_nominal']
        
        # 3. Вычисляем (K_пд * (U_борт / U_ном))
        denominator = device_data['coeff_efficiency'] * voltage_ratio
        
        # 4. Вычисляем (K_запаса / denominator)
        part2 = device_data['coeff_reserve'] / denominator
        
        # 5. Итоговая сила тока для одного устройства
        amperage_per_device = part1 * part2
        
        # 6. Умножаем на количество устройств
        total_amperage = amperage_per_device * amount
        
        return round(total_amperage, 2), True, "Успешно"
        
    except Exception as e:
        return 0, False, f"Ошибка вычисления: {str(e)}"

# ------------------- Асинхронный расчет заявки -------------------
def calculate_current_async(current_data):
    """
    Асинхронный расчет всей заявки с задержкой 5-10 секунд
    """
    try:
        current_id = current_data["current_id"]
        voltage_bord = current_data["voltage_bord"]
        devices = current_data["devices"]
        
        # Имитация долгого расчета
        calculation_time = random.randint(5, 10)
        print(f"[ASYNC] Начинаем расчёт для заявки {current_id} - {calculation_time} сек.")
        time.sleep(calculation_time)
        
        total_amperage = 0
        device_results = []
        
        # Расчет для каждого устройства
        for device in devices:
            device_id = device.get('device_id')
            amount = device.get('amount', 1)
            
            device_amperage, success, message = calculate_device_amperage(
                device_data={
                    'power_nominal': device.get('power_nominal', 0),
                    'resistance': device.get('resistance', 1),
                    'voltage_nominal': device.get('voltage_nominal', 220),
                    'coeff_efficiency': device.get('coeff_efficiency', 0.9),
                    'coeff_reserve': device.get('coeff_reserve', 1.2)
                },
                voltage_bord=voltage_bord,
                amount=amount
            )
            
            if success:
                total_amperage += device_amperage
                
                device_results.append({
                    "device_id": device_id,
                    "amperage": device_amperage,
                    "amount": amount,
                    "success": True
                })
                print(f"  Устройство {device_id}: {device_amperage} А ({amount} шт.)")
            else:
                device_results.append({
                    "device_id": device_id,
                    "amperage": 0,
                    "amount": amount,
                    "success": False,
                    "error": message
                })
                print(f"  ❌ Устройство {device_id}: ошибка - {message}")
        
        return {
            "current_id": current_id,
            "total_amperage": round(total_amperage, 2),
            "device_results": device_results,
            "calculation_time": calculation_time,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Ошибка при расчёте заявки: {e}")
        return {
            "current_id": current_data.get("current_id", 0),
            "total_amperage": 0,
            "device_results": [],
            "success": False,
            "error": str(e)
        }

# ------------------- Колбэк для отправки результатов -------------------
def send_results_to_go_server(task):
    """Отправка результатов расчета в Go сервер"""
    try:
        result = task.result()
        
        if not result['success']:
            print(f"❌ Расчёт не удался для заявки {result['current_id']}")
            return
        
        current_id = result['current_id']
        
        print(f"\n[→] Отправка результатов для заявки {current_id}:")
        print(f"    Общая сила тока: {result['total_amperage']} А")
        
        headers = {
            "Authorization": AUTH_TOKEN,
            "Content-Type": "application/json"
        }
        
        # 1. Отправляем общую силу тока заявки
        if result['total_amperage'] > 0:
            current_url = f"{GO_SERVER_URL}/current-calculations/{current_id}/total-amperage"
            current_payload = {"total_amperage": result["total_amperage"]}
            
            try:
                response = requests.put(current_url, json=current_payload, headers=headers, timeout=10)
                print(f"    Обновление заявки: {response.status_code}")
            except Exception as e:
                print(f"    ❌ Ошибка обновления заявки: {e}")
        
        # 2. Отправляем силу тока для каждого устройства
        for device_result in result['device_results']:
            if device_result['success']:
                device_url = f"{GO_SERVER_URL}/current-devices/{current_id}/{device_result['device_id']}"
                device_payload = {"amperage": device_result["amperage"]}
                
                try:
                    device_response = requests.put(device_url, json=device_payload, headers=headers, timeout=10)
                    print(f"    Устройство {device_result['device_id']}: {device_response.status_code}")
                except Exception as e:
                    print(f"    ❌ Ошибка устройства {device_result['device_id']}: {e}")
        
        print(f"✅ Результаты для заявки {current_id} отправлены")
        
    except Exception as e:
        print(f"❌ Ошибка в отправке результатов: {e}")

# ------------------- Основной endpoint для расчета всей заявки -------------------
@api_view(['POST'])
def calculate_current(request):
    """
    Расчет силы тока для всей заявки
    Пример запроса:
    {
        "current_id": 1,
        "voltage_bord": 230.0,
        "devices": [
            {
                "device_id": 1,
                "amount": 2,
                "power_nominal": 1000,
                "resistance": 10,
                "voltage_nominal": 220,
                "coeff_efficiency": 0.9,
                "coeff_reserve": 1.2
            }
        ]
    }
    """
    required_fields = ["current_id", "voltage_bord", "devices"]
    
    if not all(field in request.data for field in required_fields):
        return Response(
            {"error": "Отсутствуют обязательные поля: current_id, voltage_bord, devices"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    current_id = request.data["current_id"]
    voltage_bord = request.data["voltage_bord"]
    devices = request.data["devices"]
    
    # Проверяем структуру каждого устройства
    device_required = ["device_id", "amount", "power_nominal", "resistance", 
                       "voltage_nominal", "coeff_efficiency", "coeff_reserve"]
    
    for i, device in enumerate(devices):
        if not all(field in device for field in device_required):
            return Response(
                {"error": f"В устройстве {i} отсутствуют обязательные поля"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    print(f"📋 Получен запрос на расчёт заявки {current_id}")
    print(f"   Напряжение бортовой сети: {voltage_bord} В")
    print(f"   Количество типов устройств: {len(devices)}")
    
    # Запускаем асинхронный расчет
    task = executor.submit(calculate_current_async, request.data)
    task.add_done_callback(send_results_to_go_server)
    
    return Response(
        {
            "message": "Расчёт силы тока начат",
            "current_id": current_id,
            "estimated_time": "5-10 секунд",
            "devices_count": len(devices),
            "voltage_bord": voltage_bord
        },
        status=status.HTTP_202_ACCEPTED
    )

# ------------------- Endpoint для расчета одного устройства -------------------
@api_view(['POST'])
def calculate_single_device(request):
    """
    Расчет для одного устройства
    Пример запроса:
    {
        "current_id": 1,
        "device_id": 1,
        "amount": 2,
        "power_nominal": 1000,
        "resistance": 10,
        "voltage_nominal": 220,
        "coeff_efficiency": 0.9,
        "coeff_reserve": 1.2,
        "voltage_bord": 230
    }
    """
    required_fields = ["current_id", "device_id", "amount", "power_nominal", 
                      "resistance", "voltage_nominal", "coeff_efficiency", 
                      "coeff_reserve", "voltage_bord"]
    
    if not all(field in request.data for field in required_fields):
        return Response(
            {"error": "Не все поля были получены"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    current_id = request.data["current_id"]
    device_id = request.data["device_id"]
    
    print(f"🔧 Получено одно устройство для расчёта: заявка={current_id}, устройство={device_id}")
    
    # Создаем структуру для расчета
    device_data = {
        "current_id": current_id,
        "voltage_bord": request.data["voltage_bord"],
        "devices": [{
            "device_id": device_id,
            "amount": request.data["amount"],
            "power_nominal": request.data["power_nominal"],
            "resistance": request.data["resistance"],
            "voltage_nominal": request.data["voltage_nominal"],
            "coeff_efficiency": request.data["coeff_efficiency"],
            "coeff_reserve": request.data["coeff_reserve"]
        }]
    }
    
    # Запускаем асинхронный расчет
    task = executor.submit(calculate_current_async, device_data)
    task.add_done_callback(send_results_to_go_server)
    
    return Response(
        {
            "message": "Расчёт одного устройства начался",
            "current_id": current_id,
            "device_id": device_id,
            "estimated_time": "5-10 секунд"
        },
        status=status.HTTP_202_ACCEPTED
    )

# ------------------- Health check -------------------
@api_view(['GET'])
def health_check(request):
    """Проверка здоровья сервиса"""
    return Response(
        {
            "status": "healthy",
            "service": "async-current-calculator",
            "description": "Асинхронный сервис для расчёта силы тока заявок"
        },
        status=status.HTTP_200_OK
    )

# ------------------- Test endpoint для быстрой проверки -------------------
@api_view(['POST'])
def test_calculation(request):
    """
    Тестовый endpoint для проверки расчета без задержки
    Возвращает результат сразу (без 5-10 секунд ожидания)
    """
    if "current_id" in request.data and "voltage_bord" in request.data and "devices" in request.data:
        # Выполняем расчет без задержки
        result = calculate_current_async(request.data)
        
        # Убираем задержку из результата для теста
        if "calculation_time" in result:
            result["calculation_time"] = 0
        
        return Response(result, status=status.HTTP_200_OK)
    
    return Response(
        {"error": "Нужны current_id, voltage_bord и devices"}, 
        status=status.HTTP_400_BAD_REQUEST
    )