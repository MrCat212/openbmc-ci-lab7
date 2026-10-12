import os
import pytest
import requests

from dotenv import load_dotenv


# Загружаем настройки из .env, если файл существует
load_dotenv()


# Настройки подключения к OpenBMC
REDFISH_URL = os.getenv(
    "REDFISH_URL",
    "https://127.0.0.1:2443"
)

USERNAME = os.getenv("REDFISH_USERNAME")
PASSWORD = os.getenv("REDFISH_PASSWORD")


@pytest.fixture(scope="session")
def redfish_session():
    """
    Создаёт HTTP-сессию для тестирования Redfish API.

    Логин и пароль поступают из Jenkins Credentials
    через переменные окружения.
    """

    if not USERNAME or not PASSWORD:
        pytest.fail(
            "Не заданы REDFISH_USERNAME или REDFISH_PASSWORD"
        )

    session = requests.Session()

    # Авторизация в OpenBMC
    session.auth = (USERNAME, PASSWORD)

    # Самоподписанный сертификат OpenBMC
    session.verify = False

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def openbmc_url():
    """
    Возвращает базовый адрес Redfish API.
    """
    return REDFISH_URL
