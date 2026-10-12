import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# Настройки OpenBMC Redfish API
# ============================================================

OPENBMC_URL = os.getenv(
    "OPENBMC_URL",
    "https://127.0.0.1:2443"
)

USERNAME = os.getenv(
    "OPENBMC_USERNAME",
    "root"
)

PASSWORD = os.getenv(
    "OPENBMC_PASSWORD",
    "0penBmc"
)


# Отключаем предупреждения HTTPS
requests.packages.urllib3.disable_warnings()


# ============================================================
# Создание Redfish-сессии
# ============================================================

@pytest.fixture(scope="session")
def redfish_session():
    """
    Создаёт сессию для работы с OpenBMC Redfish API.
    """

    session = requests.Session()

    session.auth = (
        USERNAME,
        PASSWORD
    )

    session.verify = False

    return session


# ============================================================
# Базовый URL OpenBMC
# ============================================================

@pytest.fixture(scope="session")
def openbmc_url():
    """
    Возвращает адрес OpenBMC.
    """

    return OPENBMC_URL
