import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# НАСТРОЙКИ
# ============================================================

load_dotenv()

WEB_UI_URL = os.getenv(
    "WEB_UI_URL",
    "http://localhost:8000"
)

TEST_USERNAME = os.getenv(
    "TEST_USERNAME",
    "seleniumtest"
)

TEST_PASSWORD = os.getenv(
    "TEST_PASSWORD",
    ""
)

WRONG_PASSWORD = os.getenv(
    "WRONG_PASSWORD",
    ""
)


# ============================================================
# СОЗДАНИЕ FIREFOX WEBDRIVER
# ============================================================

def create_driver():
    """
    Создаёт Firefox WebDriver.

    Локально используется установленный Firefox.
    В Jenkins браузер запускается в headless-режиме.
    """

    options = Options()

    # Jenkins работает без графического интерфейса.
    if os.getenv("HEADLESS", "0") == "1":
        options.add_argument("-headless")

    # При необходимости путь к Firefox можно передать
    # через переменную окружения FIREFOX_BINARY.
    firefox_binary = os.getenv("FIREFOX_BINARY")

    if firefox_binary:
        options.binary_location = firefox_binary

    elif os.path.exists("/usr/bin/firefox-esr"):
        # Firefox внутри Jenkins Docker.
        options.binary_location = "/usr/bin/firefox-esr"

    elif os.path.exists("/usr/bin/firefox"):
        # Обычный Firefox.
        options.binary_location = "/usr/bin/firefox"

    elif os.path.exists(
        "/snap/firefox/8763/usr/lib/firefox/firefox"
    ):
        # Firefox на основном Linux.
        options.binary_location = (
            "/snap/firefox/8763/usr/lib/firefox/firefox"
        )

    driver = webdriver.Firefox(
        options=options
    )

    driver.set_window_size(1280, 900)

    return driver


# ============================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ УСПЕШНОГО ВХОДА
# ============================================================

def perform_successful_login():
    """
    Выполняет успешную авторизацию.
    """

    driver = create_driver()

    try:
        driver.get(
            f"{WEB_UI_URL}/login.html"
        )

        username = WebDriverWait(
            driver,
            10
        ).until(
            EC.presence_of_element_located(
                (By.ID, "username")
            )
        )

        password = driver.find_element(
            By.ID,
            "password"
        )

        login_button = driver.find_element(
            By.ID,
            "loginButton"
        )

        username.clear()
        username.send_keys(TEST_USERNAME)

        password.clear()
        password.send_keys(TEST_PASSWORD)

        login_button.click()

        result = WebDriverWait(
            driver,
            10
        ).until(
            EC.presence_of_element_located(
                (By.ID, "result")
            )
        )

        WebDriverWait(
            driver,
            10
        ).until(
            lambda d: (
                "успеш" in result.text.lower()
                or "success" in result.text.lower()
            )
        )

    finally:
        driver.quit()


# ============================================================
# СБРОС СЧЁТЧИКА НЕУДАЧНЫХ ПОПЫТОК
# ============================================================

def reset_failed_login_counter():
    """
    Успешный вход сбрасывает счётчик
    предыдущих неудачных попыток входа.
    """

    print(
        "\n--- Подготовка к тесту блокировки ---"
    )

    perform_successful_login()

    print(
        "Счётчик неудачных попыток сброшен"
    )


# ============================================================
# ТЕСТ 1
# УСПЕШНАЯ АВТОРИЗАЦИЯ
# ============================================================

def test_successful_login():
    print(
        "\n=== ТЕСТ 1: успешная авторизация ==="
    )

    driver = create_driver()

    try:
        driver.get(
            f"{WEB_UI_URL}/login.html"
        )

        username = WebDriverWait(
            driver,
            10
        ).until(
            EC.presence_of_element_located(
                (By.ID, "username")
            )
        )

        password = driver.find_element(
            By.ID,
            "password"
        )

        login_button = driver.find_element(
            By.ID,
            "loginButton"
        )

        username.send_keys(TEST_USERNAME)
        password.send_keys(TEST_PASSWORD)

        login_button.click()

        result = WebDriverWait(
            driver,
            10
        ).until(
            EC.presence_of_element_located(
                (By.ID, "result")
            )
        )

        WebDriverWait(
            driver,
            10
        ).until(
            lambda d: (
                "успеш" in result.text.lower()
                or "success" in result.text.lower()
            )
        )

        print(
            "PASS: авторизация выполнена успешно"
        )

    finally:
        driver.quit()


# ============================================================
# ТЕСТ 2
# НЕВЕРНЫЕ УЧЁТНЫЕ ДАННЫЕ
# ============================================================

def test_invalid_credentials():
    print(
        "\n=== ТЕСТ 2: неверные учётные данные ==="
    )

    driver = create_driver()

    try:
        driver.get(
            f"{WEB_UI_URL}/login.html"
        )

        username = WebDriverWait(
            driver,
            10
        ).until(
            EC.presence_of_element_located(
                (By.ID, "username")
            )
        )

        password = driver.find_element(
            By.ID,
            "password"
        )

        login_button = driver.find_element(
            By.ID,
            "loginButton"
        )

        username.send_keys(TEST_USERNAME)
        password.send_keys(WRONG_PASSWORD)

        login_button.click()

        result = WebDriverWait(
            driver,
            10
        ).until(
            EC.presence_of_element_located(
                (By.ID, "result")
            )
        )

        WebDriverWait(
            driver,
            10
        ).until(
            lambda d: (
                result.text.strip() != ""
            )
        )

        assert (
            "успеш" not in result.text.lower()
            and "success" not in result.text.lower()
        )

        print(
            "PASS: OpenBMC отклонил "
            "неправильные учётные данные"
        )

    finally:
        driver.quit()


# ============================================================
# ТЕСТ 3
# БЛОКИРОВКА УЧЁТНОЙ ЗАПИСИ
# ============================================================

def test_account_lockout():
    reset_failed_login_counter()

    print(
        "\n=== ТЕСТ 3: блокировка учётной записи ==="
    )

    driver = create_driver()

    try:
        driver.get(
            f"{WEB_UI_URL}/login.html"
        )

        for attempt in range(1, 4):
            username = WebDriverWait(
                driver,
                10
            ).until(
                EC.presence_of_element_located(
                    (By.ID, "username")
                )
            )

            password = driver.find_element(
                By.ID,
                "password"
            )

            login_button = driver.find_element(
                By.ID,
                "loginButton"
            )

            username.clear()
            password.clear()

            username.send_keys(TEST_USERNAME)
            password.send_keys(WRONG_PASSWORD)

            login_button.click()

            WebDriverWait(
                driver,
                10
            ).until(
                lambda d: (
                    d.find_element(
                        By.ID,
                        "result"
                    ).text.strip() != ""
                )
            )

            print(
                f"Неудачная попытка {attempt}/3"
            )

            time.sleep(1)

        print(
            "Пробуем войти с правильным "
            "паролем после трёх ошибок..."
        )

        username = driver.find_element(
            By.ID,
            "username"
        )

        password = driver.find_element(
            By.ID,
            "password"
        )

        login_button = driver.find_element(
            By.ID,
            "loginButton"
        )

        username.clear()
        password.clear()

        username.send_keys(TEST_USERNAME)
        password.send_keys(TEST_PASSWORD)

        login_button.click()

        result = WebDriverWait(
            driver,
            10
        ).until(
            EC.presence_of_element_located(
                (By.ID, "result")
            )
        )

        WebDriverWait(
            driver,
            10
        ).until(
            lambda d: (
                result.text.strip() != ""
            )
        )

        assert (
            "успеш" not in result.text.lower()
            and "success" not in result.text.lower()
        )

        print(
            "PASS: после трёх неправильных попыток "
            "учётная запись заблокирована"
        )

    finally:
        driver.quit()


# ============================================================
# ТЕСТ 4
# ОТОБРАЖЕНИЕ ИНВЕНТАРИЗАЦИИ
# ============================================================

def test_inventory_display():
    print(
        "\n=== ТЕСТ 4: отображение инвентаризации ==="
    )

    driver = create_driver()

    try:
        driver.get(
            f"{WEB_UI_URL}/inventory.html"
        )

        load_button = WebDriverWait(
            driver,
            10
        ).until(
            EC.element_to_be_clickable(
                (By.ID, "loadInventoryButton")
            )
        )

        load_button.click()

        # Ждём завершения асинхронной загрузки, а не первого
        # непустого текста: изначально в полях стоит "-".
        def inventory_loaded(d):
            status = d.find_element(By.ID, "status").text.strip()

            if status.startswith("Ошибка"):
                raise AssertionError(
                    f"Не удалось загрузить инвентаризацию: {status}"
                )

            return status == "Инвентаризация успешно загружена"

        WebDriverWait(driver, 30).until(inventory_loaded)

        system_name = driver.find_element(
            By.ID,
            "systemName"
        ).text.strip()

        system_type = driver.find_element(
            By.ID,
            "systemType"
        ).text.strip()

        power_state = driver.find_element(
            By.ID,
            "powerState"
        ).text.strip()

        health = driver.find_element(
            By.ID,
            "health"
        ).text.strip()

        processor_count = driver.find_element(
            By.ID,
            "processorCount"
        ).text.strip()

        memory_gib = driver.find_element(
            By.ID,
            "memoryGiB"
        ).text.strip()

        print(
            "Полученные через Web UI данные:"
        )

        print(
            f"Имя системы: {system_name}"
        )

        print(
            f"Тип системы: {system_type}"
        )

        print(
            f"Состояние питания: {power_state}"
        )

        print(
            f"Состояние здоровья: {health}"
        )

        print(
            f"Количество процессоров: "
            f"{processor_count}"
        )

        print(
            f"Оперативная память, GiB: "
            f"{memory_gib}"
        )

        invalid_values = {
            "",
            "-",
            "undefined",
            "null",
            "none"
        }

        assert (
            system_name.lower()
            not in invalid_values
        )

        assert (
            system_type.lower()
            not in invalid_values
        )

        assert (
            power_state.lower()
            not in invalid_values
        )

        assert (
            health.lower()
            not in invalid_values
        )

        assert (
            processor_count.lower()
            not in invalid_values
        )

        assert (
            memory_gib.lower()
            not in invalid_values
        )

        assert float(processor_count) >= 0
        assert float(memory_gib) >= 0

        print(
            "PASS: инвентаризация OpenBMC "
            "корректно отображается через Web UI"
        )

    finally:
        driver.quit()


# ============================================================
# ТЕСТ 5
# POWER ON + ПРОВЕРКА JOURNAL
# ============================================================

def test_power_on_creates_journal_event():
    print(
        "\n=== ТЕСТ 5: Power On и событие в Journal ==="
    )

    driver = create_driver()

    try:
        driver.get(
            f"{WEB_UI_URL}/journal.html"
        )

        load_journal_button = WebDriverWait(
            driver,
            10
        ).until(
            EC.element_to_be_clickable(
                (By.ID, "loadJournalButton")
            )
        )

        load_journal_button.click()

        WebDriverWait(
            driver,
            30
        ).until(
            lambda d: (
                d.find_element(
                    By.ID,
                    "powerEntryCount"
                ).text.strip().isdigit()
            )
        )

        before_count = int(
            driver.find_element(
                By.ID,
                "powerEntryCount"
            ).text.strip()
        )

        print(
            f"Событий Power On до действия: "
            f"{before_count}"
        )

        power_on_button = driver.find_element(
            By.ID,
            "powerOnButton"
        )

        power_on_button.click()

        WebDriverWait(
            driver,
            15
        ).until(
            lambda d: (
                d.find_element(
                    By.ID,
                    "powerStatus"
                ).text.strip() != ""
            )
        )

        print(
            "Команда Power On отправлена"
        )

        # OpenBMC может добавить событие в Journal
        # не мгновенно.
        time.sleep(15)

        def new_power_event_appeared(d):
            load_button = d.find_element(
                By.ID,
                "loadJournalButton"
            )

            load_button.click()

            time.sleep(2)

            value = d.find_element(
                By.ID,
                "powerEntryCount"
            ).text.strip()

            if not value.isdigit():
                return False

            current_count = int(value)

            print(
                "Текущее количество Power On "
                f"событий: {current_count}"
            )

            return current_count > before_count

        WebDriverWait(
            driver,
            120,
            poll_frequency=5
        ).until(
            new_power_event_appeared
        )

        after_count = int(
            driver.find_element(
                By.ID,
                "powerEntryCount"
            ).text.strip()
        )

        print(
            f"Событий Power On после действия: "
            f"{after_count}"
        )

        assert after_count > before_count

        print(
            "PASS: после Power On появились "
            "новые события в BMC Journal"
        )

    finally:
        driver.quit()


# ============================================================
# ЗАПУСК ВСЕХ ТЕСТОВ
# ============================================================

if __name__ == "__main__":

    test_successful_login()

    test_invalid_credentials()

    test_account_lockout()

    test_inventory_display()

    test_power_on_creates_journal_event()
