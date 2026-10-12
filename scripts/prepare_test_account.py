import os
import requests
import urllib3


# Самоподписанный сертификат OpenBMC
urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# Настройки получаем из Jenkins Credentials
OPENBMC_URL = os.environ["OPENBMC_URL"].rstrip("/")

ADMIN_USERNAME = os.environ["OPENBMC_USERNAME"]
ADMIN_PASSWORD = os.environ["OPENBMC_PASSWORD"]

TEST_USERNAME = os.environ["WEBUI_USERNAME"]
TEST_PASSWORD = os.environ["WEBUI_PASSWORD"]


# Создаём HTTP-сессию администратора
session = requests.Session()

session.auth = (
    ADMIN_USERNAME,
    ADMIN_PASSWORD
)

session.verify = False


def request(method, path, **kwargs):
    """
    Отправляет запрос к Redfish API.
    При ошибке останавливает выполнение.
    """

    response = session.request(
        method,
        f"{OPENBMC_URL}{path}",
        timeout=20,
        **kwargs
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Redfish {method} {path}: "
            f"HTTP {response.status_code}, "
            f"{response.text[:500]}"
        )

    return response


def prepare_account():
    """
    Создаёт тестового пользователя,
    если он отсутствует.

    Если пользователь уже существует,
    обновляет настройки и разблокирует его.
    """

    print("=== Подготовка учётной записи Selenium ===")

    accounts_path = "/redfish/v1/AccountService/Accounts"

    response = request("GET", accounts_path)

    accounts = response.json().get("Members", [])

    existing_account_path = None

    # Ищем пользователя по имени
    for account in accounts:

        path = account.get("@odata.id")

        if not path:
            continue

        account_response = request("GET", path)

        data = account_response.json()

        if data.get("UserName") == TEST_USERNAME:
            existing_account_path = path
            break

    if existing_account_path:

        print("Тестовый пользователь уже существует")

        # Обновляем пароль и снимаем блокировку
        request(
            "PATCH",
            existing_account_path,
            json={
                "Password": TEST_PASSWORD,
                "Enabled": True,
                "Locked": False,
                "RoleId": "Administrator"
            }
        )

        print("Учётная запись обновлена и разблокирована")

    else:

        print("Создаём тестового пользователя")

        request(
            "POST",
            accounts_path,
            json={
                "UserName": TEST_USERNAME,
                "Password": TEST_PASSWORD,
                "RoleId": "Administrator",
                "Enabled": True
            }
        )

        print("Тестовый пользователь создан")

    # Для Selenium-теста блокировки:
    # 3 неправильных попытки, блокировка на 60 секунд.
    request(
        "PATCH",
        "/redfish/v1/AccountService",
        json={
            "AccountLockoutThreshold": 3,
            "AccountLockoutDuration": 60
        }
    )

    print("Настроена блокировка после 3 ошибок")

    # Проверяем, что тестовая учётка действительно работает
    check = requests.get(
        f"{OPENBMC_URL}{accounts_path}",
        auth=(TEST_USERNAME, TEST_PASSWORD),
        verify=False,
        timeout=20
    )

    if check.status_code != 200:
        raise RuntimeError(
            "Тестовый пользователь не может авторизоваться: "
            f"HTTP {check.status_code}"
        )

    print("PASS: тестовый пользователь успешно авторизуется")


if __name__ == "__main__":
    try:
        prepare_account()
    finally:
        session.close()
