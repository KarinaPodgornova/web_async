from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
import time, random
from concurrent.futures import ThreadPoolExecutor

GO_URL = "http://127.0.0.1/api/v1"   # ← поменяешь если нужно
AUTH = "secret123"

executor = ThreadPoolExecutor(max_workers=10)

###############################################
# 1. Расчёт одного устройства
###############################################
@api_view(['POST'])
def calculate_single_device(request):
    required = ["current_id", "device_id", "power", "amount", "voltage_bord"]

    if not all(k in request.data for k in required):
        return Response({"error": "not enough fields"}, status=400)

    current_id = request.data["current_id"]
    device_id = request.data["device_id"]
    power      = request.data["power"]         # P ном
    amount     = request.data["amount"]        # кол-во
    voltage    = request.data["voltage_bord"]  # напряжение заявки

    def async_calc():
        time.sleep(random.randint(4,8))  # имитация асинхронности
        amperage = (power/voltage) * amount   # простая формула из твоей 4 лабы 

        # отправляем результат в GO API
        url = f"{GO_URL}/current-devices/{current_id}/{device_id}"
        payload = { "amperage": amperage }
        headers = {"Authorization": AUTH}

        r = requests.put(url, json=payload, headers=headers)
        print("Update device amperage:", r.status_code)

    executor.submit(async_calc)

    return Response({"status": "accepted", "device": device_id}, status=202)


###############################################
# 2. Запуск расчёта всей заявки (всех устройств)
###############################################
@api_view(['POST'])
def calculate_entire_current(request):
    if "current_id" not in request.data:
        return Response({"error": "current_id required"}, status=400)

    current_id = request.data["current_id"]

    # 🔥 Забираем все устройства в этой заявке из Go
    url = f"{GO_URL}/current-calculations/{current_id}"
    data = requests.get(url).json()

    if "devices" not in data:
        return Response({"error": "Go did not return devices"}, status=500)

    for dev in data["devices"]:
        executor.submit(calculate_single_device, type("Mock", (), {
            "data": {
                "current_id": current_id,
                "device_id": dev["device_id"],
                "power": dev["power_nominal"],
                "amount": dev["amount"],
                "voltage_bord": data["voltage_bord"]
            }
        }))

    return Response({"status": "started_all", "devices": len(data["devices"])})
    

###############################################
@api_view(['GET'])
def health_check(request):
    return Response({"ok": True})
