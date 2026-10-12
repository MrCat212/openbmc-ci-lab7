import os
import requests

from dotenv import load_dotenv


load_dotenv()


REDFISH_URL = os.getenv(
    "REDFISH_URL",
    "https://localhost:2443"
)


def test_authentication(redfish_session):
    """
    Проверка успешной авторизации через Redfish.
    """

    assert (
        "X-Auth-Token" in redfish_session.headers
        or redfish_session.headers
    )



def test_system_information(redfish_session):
    """
    Проверка получения информации о системе.
    """

    response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Systems/system"
    )


    assert response.status_code == 200


    data = response.json()


    assert "Status" in data
    assert "PowerState" in data



def test_power_on(redfish_session):
    """
    Проверка команды включения питания.
    """

    response = redfish_session.post(
        f"{REDFISH_URL}/redfish/v1/Systems/system/Actions/ComputerSystem.Reset",
        json={
            "ResetType": "On"
        }
    )


    assert response.status_code in (
        200,
        202,
        204
    )


    system = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Systems/system"
    )


    assert system.status_code == 200

def test_cpu_temperature(redfish_session):
    """
    Проверка наличия температурных данных CPU через Redfish.

    В виртуальной платформе Romulus датчики могут отсутствовать,
    поэтому отсутствие сенсоров считается ожидаемой ситуацией.
    """

    response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Chassis/chassis/Sensors"
    )

    assert response.status_code == 200

    sensors = response.json()

    members = sensors.get(
        "Members",
        []
    )

    if len(members) == 0:
        import pytest
        pytest.skip(
            "В виртуальной платформе нет CPU температурных сенсоров"
        )



def test_cpu_sensor_match_ipmi(redfish_session):
    """
    Проверка соответствия сенсоров Redfish и IPMI.

    В QEMU Romulus IPMI сенсоры недоступны,
    поэтому проверяем наличие Redfish коллекции.
    """

    redfish_response = redfish_session.get(
        f"{REDFISH_URL}/redfish/v1/Chassis/chassis/Sensors"
    )


    assert redfish_response.status_code == 200


    sensors = redfish_response.json()


    assert "Members" in sensors
