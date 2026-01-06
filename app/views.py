from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import time
import random
import requests
from concurrent import futures
import math

# Адрес твоего Go сервиса и токен авторизации
MAIN_SERVICE_URL = "http://localhost:80/api/v1" 
AUTH_TOKEN = "secret123"  # Тот же токен, что в Go сервисе

executor = futures.ThreadPoolExecutor(max_workers=5)

def calculate_device_current_single(current_id, device_id, dev_power, amount):
    """Асинхронное вычисление силы тока одного устройства"""
    try:
        calculation_time = random.randint(5, 10)
        print(f"Начинаем расчёт для заявки {current_id}, устройство {device_id} - расчёт займёт {calculation_time} секунд")
        time.sleep(calculation_time)

        if amount and amount > 0:
            
            amperage = (dev_power * 0.0045) * amount  # 0.0045 - примерный коэффициент
            success = True
            print(f"Расчёт выполнен: устройство {device_id}, сила тока = {amperage:.2f} A")
        else:
            amperage = 0
            success = False
            print(f"Ошибка при расчёте: неправильное количество = {amount}")
        
        return {
            "current_id": current_id,
            "device_id": device_id,
            "amperage": amperage,
            "amount": amount,  # Сохраняем amount для отправки обратно
            "success": success,
            "calculation_time": calculation_time
        }
    except Exception as e:
        print(f"Ошибка при расчёте устройства {device_id}: {e}")
        return {
            "current_id": current_id,
            "device_id": device_id,
            "amperage": 0,
            "success": False,
            "error": str(e)
        }

def send_calculation_result(task):
    """Колбэк для отправки результата одного устройства в основной сервис"""
    try:
        result = task.result()
        print(f"Отправка результатов для заявки {result['current_id']}, устройство {result['device_id']}: {result['amperage']} A")
        
        if result['success']:
            update_url = f"{MAIN_SERVICE_URL}/current-calculations/{result['current_id']}/device_amperage"
            
            payload = {
                "device_id": result["device_id"],
                "amperage": result["amperage"],
                "amount": result.get("amount"),  # Передаем amount, если он есть
            }
            
            headers = {
                "Authorization": AUTH_TOKEN,
                "Content-Type": "application/json"
            }
            
            response = requests.put(update_url, json=payload, headers=headers, timeout=10)
            
            print(f"Ответ на обновление устройства {result['device_id']}: {response.status_code}")
            if response.status_code == 200:
                print(f"Успешно обновлена сила тока для устройства {result['device_id']}")
            else:
                print(f"Ошибка в обновлении силы тока для устройства {result['device_id']}: {response.text}")
        else:
            print(f"Расчёт не удался для устройства {result['device_id']}, не отправлен результат")
        
    except Exception as e:
        print(f"Ошибка в отправке расчёта: {e}")

@api_view(['POST'])
def calculate_current(request):
    """Запуск расчета силы тока для одного устройства"""
    required_fields = ["current_id", "device_id", "dev_power", "amount"]
    
    if all(field in request.data for field in required_fields):   
        current_id = request.data["current_id"]
        device_id = request.data["device_id"] 
        dev_power = request.data["dev_power"]
        amount = request.data["amount"]
        
        print(f"Получено одно устройство для расчёта: заявка={current_id}, устройство={device_id}, мощность={dev_power}, количество={amount}")
        
        task = executor.submit(
            calculate_device_current_single, 
            current_id, 
            device_id, 
            dev_power,
            amount
        )
        task.add_done_callback(send_calculation_result)
        
        return Response(
            {
                "message": "Расчёт силы тока устройства начался", 
                "current_id": current_id,
                "device_id": device_id,
                "estimated_time": "5-10 секунд"
            },
            status=status.HTTP_202_ACCEPTED
        )
    
    return Response(
        {"error": "Не все поля были получены"}, 
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['POST'])
def calculate_current_batch(request):
    """Запуск расчета силы тока для всех устройств в заявке"""
    if "current_id" in request.data and "devices" in request.data:   
        current_id = request.data["current_id"]
        devices = request.data["devices"]
        
        print(f"Получен запрос на расчёт силы тока для заявки {current_id}, устройств: {len(devices)}")
        
        # Получаем мощность устройств из основного сервиса
        try:
            # Для каждого устройства получаем его мощность через публичный эндпоинт /devices/:id
            devices_dict = {}
            for device_request in devices:
                device_id = device_request.get("device_id")
                if not device_id:
                    continue
                
                # Получаем информацию об устройстве (этот эндпоинт доступен без авторизации)
                device_url = f"{MAIN_SERVICE_URL}/devices/{device_id}"
                device_response = requests.get(device_url, timeout=5)
                
                if device_response.status_code == 200:
                    device_data = device_response.json()
                    power_nominal = device_data.get("power_nominal", 0)
                    devices_dict[device_id] = float(power_nominal) if power_nominal else 0
                    print(f"Получена мощность устройства {device_id}: {power_nominal} Вт")
                else:
                    print(f"Не удалось получить данные устройства {device_id}: {device_response.status_code}")
                    devices_dict[device_id] = 0
            
            # Запускаем расчет для каждого устройства
            tasks_started = 0
            for device_request in devices:
                device_id = device_request.get("device_id")
                amount = device_request.get("amount", 1)
                dev_power = devices_dict.get(device_id, 0)
                
                if not dev_power or dev_power == 0:
                    print(f"Мощность устройства {device_id} не указана или равна 0, пропускаем")
                    continue
                
                print(f"Запуск расчёта для устройства {device_id}, мощность={dev_power}, количество={amount}")
                task = executor.submit(
                    calculate_device_current_single, 
                    current_id, 
                    device_id, 
                    float(dev_power),
                    int(amount)
                )
                task.add_done_callback(send_calculation_result)
                tasks_started += 1
            
            if tasks_started == 0:
                return Response(
                    {"error": "Не удалось запустить расчёт ни для одного устройства"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(
                {
                    "message": "Начат расчёт силы тока для всех устройств", 
                    "current_id": current_id,
                    "devices_count": tasks_started,
                    "estimated_total_time": f"{tasks_started * 5}-{tasks_started * 10} секунд"
                },
                status=status.HTTP_202_ACCEPTED
            )
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении данных заявки: {e}")
            return Response(
                {"error": f"Не удалось получить данные заявки: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(
        {"error": "current_id и devices обязательны"}, 
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['GET'])
def health_check(request):
    """Проверка здоровья сервиса"""
    return Response({"status": "healthy", "service": "async-current-calculator"}, status=status.HTTP_200_OK)