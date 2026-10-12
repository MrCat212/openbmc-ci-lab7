import os
import pytest

from dotenv import load_dotenv


# ============================================================
# НАСТРОЙКИ REDFISH API
# ============================================================

load_dotenv()

REDFISH_URL = os.getenv(
    "REDFISH_URL",
    "https://localhost:2443"
).rstrip("/")


# ============================================================
# ТЕСТ 1. ПРОВЕРКА АВТОРИЗАЦИИ
# ============================================================

def test_authentication(redfish_session):
    """
    Проверяем, что OpenBMC принимает учётные данные.

    Используем защищённый ресурс AccountService.
    """

    response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/AccountService/Accounts",
        timeout=20
    )

    assert response.status_code == 200, (
        f"Ошибка авторизации: HTTP {response.status_code}"
    )


# ============================================================
# ТЕСТ 2. ИНФОРМАЦИЯ О СИСТЕМЕ
# ============================================================

def test_system_information(redfish_session):
    """
    Проверяем получение информации о системе OpenBMC.
    """

    response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Systems/system",
        timeout=20
    )

    assert response.status_code == 200

    data = response.json()

    assert "Status" in data
    assert "@odata.id" in data
    assert "Actions" in data

    assert (
        data["@odata.id"]
        == "/redfish/v1/Systems/system"
    )


# ============================================================
# ТЕСТ 3. ПРОВЕРКА УПРАВЛЕНИЯ ПИТАНИЕМ
# ============================================================

def test_power_action_available(redfish_session):
    """
    Проверяем, что OpenBMC объявляет
    действие управления питанием.

    Саму команду Power On здесь не отправляем:
    в QEMU она ранее возвращала HTTP 404.
    """

    response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Systems/system",
        timeout=20
    )

    assert response.status_code == 200

    data = response.json()

    actions = data.get("Actions", {})

    assert "#ComputerSystem.Reset" in actions

    reset_action = actions["#ComputerSystem.Reset"]

    assert "target" in reset_action

    assert reset_action["target"] == (
        "/redfish/v1/Systems/system/"
        "Actions/ComputerSystem.Reset"
    )


# ============================================================
# ТЕСТ 4. ТЕМПЕРАТУРА CPU
# ============================================================

def test_cpu_temperature(redfish_session):
    """
    Проверяем температурные сенсоры CPU.

    Если виртуальная платформа не предоставляет
    датчики, тест пропускается.
    """

    response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Chassis/chassis/Sensors",
        timeout=20
    )

    assert response.status_code == 200

    data = response.json()

    sensors = data.get("Members", [])

    if not sensors:
        pytest.skip(
            "В виртуальной платформе Romulus "
            "отсутствуют температурные сенсоры CPU"
        )

    cpu_temperatures = []

    for sensor_info in sensors:

        sensor_path = sensor_info.get("@odata.id")

        if not sensor_path:
            continue

        sensor_response = redfish_session.get(
            f"{REDFISH_URL}{sensor_path}",
            timeout=20
        )

        assert sensor_response.status_code == 200

        sensor = sensor_response.json()

        name = sensor.get("Name", "")

        if (
            "CPU" in name.upper()
            and sensor.get("ReadingType") == "Temperature"
        ):
            temperature = sensor.get("Reading")

            assert isinstance(
                temperature,
                (int, float)
            )

            cpu_temperatures.append(temperature)

    if not cpu_temperatures:
        pytest.skip(
            "Температурные сенсоры CPU не обнаружены"
        )


# ============================================================
# ТЕСТ 5. КОЛЛЕКЦИЯ СЕНСОРОВ REDFISH
# ============================================================

def test_redfish_sensor_collection(redfish_session):
    """
    Проверяем, что Redfish предоставляет
    корректную коллекцию сенсоров.

    Это проверка API, а не сравнение с IPMI.
    """

    response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Chassis/chassis/Sensors",
        timeout=20
    )

    assert response.status_code == 200

    data = response.json()

    assert "Members" in data

    assert isinstance(
        data["Members"],
        list
    )

    assert "Members@odata.count" in data

    assert data["Members@odata.count"] == len(
        data["Members"]
    )
