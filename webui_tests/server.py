from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import requests
import urllib3

from dotenv import load_dotenv


# Загружаем локальный файл .env.
# В GitHub этот файл не попадёт благодаря .gitignore.
load_dotenv()


# ============================================================
# НАСТРОЙКИ OPENBMC
# ============================================================

# URL OpenBMC можно изменить через переменную окружения.
OPENBMC_URL = os.getenv(
    "OPENBMC_URL",
    "https://localhost:2443"
)


# Логин и пароль больше не хранятся в коде.
#
# Значения берутся из окружения.
# Если переменные не заданы:
# - логин останется root (для удобства локального запуска)
# - пароль будет пустым, чтобы случайно не отправить секреты
# в GitHub.
OPENBMC_ADMIN_USERNAME = os.getenv(
    "OPENBMC_USERNAME",
    "root"
)

OPENBMC_ADMIN_PASSWORD = os.getenv(
    "OPENBMC_PASSWORD",
    ""
)


# В нашей учебной QEMU-среде OpenBMC используется
# самоподписанный HTTPS-сертификат.
urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


class OpenBMCHandler(SimpleHTTPRequestHandler):

    # ========================================================
    # ОБРАБОТКА POST-ЗАПРОСОВ
    # ========================================================

    def do_POST(self):

        if self.path == "/api/login":
            self.handle_login()
            return

        if self.path == "/api/power-on":
            self.handle_power_on()
            return

        self.send_json(
            404,
            {
                "success": False,
                "message": "Неизвестный API endpoint"
            }
        )


    # ========================================================
    # ОБРАБОТКА GET-ЗАПРОСОВ
    # ========================================================

    def do_GET(self):

        if self.path == "/api/inventory":
            self.handle_inventory()
            return

        if self.path == "/api/journal":
            self.handle_journal()
            return

        # Если это не API-запрос, используем обычную
        # раздачу HTML-файлов.
        super().do_GET()


    # ========================================================
    # АВТОРИЗАЦИЯ
    # ========================================================

    def handle_login(self):

        try:

            content_length = int(
                self.headers.get("Content-Length", 0)
            )

            body = self.rfile.read(content_length)

            data = json.loads(body)

            username = data.get("username", "")
            password = data.get("password", "")


            # Важно:
            # /redfish/v1/ использовать для проверки пароля нельзя,
            # потому что в нашем OpenBMC этот endpoint доступен
            # даже без успешной авторизации.
            #
            # Поэтому обращаемся к защищённому ресурсу.
            response = requests.get(
                OPENBMC_URL
                + "/redfish/v1/AccountService/Accounts",
                auth=(username, password),
                verify=False,
                timeout=10
            )


            print(
                f"Попытка входа пользователя {username}: "
                f"HTTP {response.status_code}"
            )


            if response.status_code == 200:

                self.send_json(
                    200,
                    {
                        "success": True,
                        "message":
                            "Авторизация выполнена успешно"
                    }
                )

            elif response.status_code == 401:

                self.send_json(
                    401,
                    {
                        "success": False,
                        "message":
                            "Неверный логин или пароль"
                    }
                )

            else:

                self.send_json(
                    502,
                    {
                        "success": False,
                        "message":
                            "OpenBMC вернул HTTP "
                            + str(response.status_code)
                    }
                )


        except Exception as error:

            print(
                "Ошибка авторизации:",
                error
            )

            self.send_json(
                500,
                {
                    "success": False,
                    "message":
                        "Ошибка связи с OpenBMC"
                }
            )


    # ========================================================
    # ИНВЕНТАРИЗАЦИЯ
    # ========================================================

    def handle_inventory(self):

        try:

            response = requests.get(
                OPENBMC_URL
                + "/redfish/v1/Systems/system",
                auth=(
                    OPENBMC_ADMIN_USERNAME,
                    OPENBMC_ADMIN_PASSWORD
                ),
                verify=False,
                timeout=10
            )


            print(
                "Запрос инвентаризации: HTTP",
                response.status_code
            )


            if response.status_code != 200:

                self.send_json(
                    502,
                    {
                        "success": False,
                        "message":
                            "Не удалось получить "
                            "инвентаризацию OpenBMC"
                    }
                )

                return


            data = response.json()


            # Получаем реальные данные из Redfish.
            inventory = {

                "system_name":
                    data.get("Name", "-"),

                "system_type":
                    data.get("SystemType", "-"),

                "power_state":
                    data.get("PowerState", "-"),

                "health":
                    data.get(
                        "Status", {}
                    ).get(
                        "Health", "-"
                    ),

                "processor_count":
                    data.get(
                        "ProcessorSummary", {}
                    ).get(
                        "Count", "-"
                    ),

                "memory_gib":
                    data.get(
                        "MemorySummary", {}
                    ).get(
                        "TotalSystemMemoryGiB", "-"
                    )
            }


            self.send_json(
                200,
                {
                    "success": True,
                    "inventory": inventory
                }
            )


        except Exception as error:

            print(
                "Ошибка получения инвентаризации:",
                error
            )

            self.send_json(
                500,
                {
                    "success": False,
                    "message":
                        "Ошибка получения инвентаризации"
                }
            )


    # ========================================================
    # POWER ON
    # ========================================================

    def handle_power_on(self):

        try:

            print(
                "\n=== Отправка Power On в OpenBMC ==="
            )


            response = requests.post(
                OPENBMC_URL
                + "/redfish/v1/Systems/system/"
                  "Actions/ComputerSystem.Reset",
                auth=(
                    OPENBMC_ADMIN_USERNAME,
                    OPENBMC_ADMIN_PASSWORD
                ),
                verify=False,
                timeout=10,
                json={
                    "ResetType": "On"
                }
            )


            print(
                "OpenBMC ответил:",
                response.status_code
            )


            # Redfish action может вернуть 200, 202 или 204.
            #
            # Здесь мы проверяем только то, что OpenBMC
            # принял команду.
            #
            # Мы НЕ утверждаем, что виртуальный host
            # действительно успешно включился.
            if response.status_code in (
                200,
                202,
                204
            ):

                self.send_json(
                    200,
                    {
                        "success": True,
                        "message":
                            "Команда Power On "
                            "отправлена в OpenBMC"
                    }
                )

            else:

                self.send_json(
                    502,
                    {
                        "success": False,
                        "message":
                            "OpenBMC отклонил команду. HTTP "
                            + str(response.status_code)
                    }
                )


        except Exception as error:

            print(
                "Ошибка Power On:",
                error
            )

            self.send_json(
                500,
                {
                    "success": False,
                    "message":
                        "Ошибка отправки Power On"
                }
            )


    # ========================================================
    # BMC JOURNAL
    # ========================================================

    def handle_journal(self):

        try:

            print(
                "\n=== Чтение BMC Journal ==="
            )


            # ------------------------------------------------
            # ВАЖНО:
            #
            # Redfish не обязательно возвращает весь журнал
            # одним ответом.
            #
            # Например, у нас журнал уже содержит больше
            # 1000 записей.
            #
            # Следующая страница указывается в:
            #
            # Members@odata.nextLink
            #
            # Поэтому читаем страницы в цикле.
            # ------------------------------------------------

            next_path = (
                "/redfish/v1/Managers/bmc/"
                "LogServices/Journal/Entries"
            )

            all_entries = []

            total_count = 0

            page_number = 0


            while next_path:

                page_number += 1

                print(
                    f"Читаем страницу Journal №{page_number}"
                )


                response = requests.get(
                    OPENBMC_URL + next_path,
                    auth=(
                        OPENBMC_ADMIN_USERNAME,
                        OPENBMC_ADMIN_PASSWORD
                    ),
                    verify=False,
                    timeout=20
                )


                print(
                    "HTTP:",
                    response.status_code
                )


                if response.status_code != 200:

                    self.send_json(
                        502,
                        {
                            "success": False,
                            "message":
                                "Не удалось получить "
                                "BMC Journal"
                        }
                    )

                    return


                data = response.json()


                # На первой странице Redfish сообщает
                # общее количество записей.
                if page_number == 1:

                    total_count = data.get(
                        "Members@odata.count",
                        0
                    )


                members = data.get(
                    "Members",
                    []
                )


                print(
                    "Записей на странице:",
                    len(members)
                )


                all_entries.extend(
                    members
                )


                # Если следующей страницы нет,
                # data.get() вернёт None и цикл закончится.
                next_path = data.get(
                    "Members@odata.nextLink"
                )


                # Защита от случайного бесконечного цикла.
                # Для нашей лабораторной 20 страниц
                # более чем достаточно.
                if page_number >= 20:

                    print(
                        "Достигнут лимит в 20 страниц"
                    )

                    break


            print(
                "Всего Redfish сообщает записей:",
                total_count
            )

            print(
                "Фактически загружено записей:",
                len(all_entries)
            )


            # ------------------------------------------------
            # ИЩЕМ СОБЫТИЯ, СВЯЗАННЫЕ С POWER ON
            # ------------------------------------------------

            power_entries = []


            for entry in all_entries:

                message = entry.get(
                    "Message",
                    ""
                )

                message_lower = message.lower()


                # В нашем OpenBMC встречаются оба варианта:
                #
                # "Power On"
                #
                # и
                #
                # "poweron"
                if (
                    "power on" in message_lower
                    or
                    "poweron" in message_lower
                ):

                    power_entries.append(
                        {
                            # Id пригодится нам для Selenium:
                            # по нему можно отличить старую запись
                            # от новой.
                            "id":
                                str(
                                    entry.get(
                                        "Id",
                                        ""
                                    )
                                ),

                            "created":
                                entry.get(
                                    "Created",
                                    ""
                                ),

                            "severity":
                                entry.get(
                                    "Severity",
                                    ""
                                ),

                            "message":
                                message
                        }
                    )


            print(
                "Найдено событий Power On:",
                len(power_entries)
            )


            self.send_json(
                200,
                {
                    "success": True,

                    # Сколько записей сообщает сам Redfish.
                    "total_count":
                        total_count,

                    # Сколько записей реально получили,
                    # пройдя по страницам.
                    "loaded_count":
                        len(all_entries),

                    # Все найденные Power On события.
                    "power_entries":
                        power_entries
                }
            )


        except Exception as error:

            print(
                "Ошибка получения Journal:",
                error
            )

            self.send_json(
                500,
                {
                    "success": False,
                    "message":
                        "Ошибка получения BMC Journal"
                }
            )


    # ========================================================
    # ОТПРАВКА JSON В БРАУЗЕР
    # ========================================================

    def send_json(
        self,
        status_code,
        data
    ):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode(
            "utf-8"
        )


        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )


# ============================================================
# ЗАПУСК ЛОКАЛЬНОГО WEB UI
# ============================================================

if __name__ == "__main__":

    server_address = (
        "localhost",
        8000
    )


    httpd = ThreadingHTTPServer(
        server_address,
        OpenBMCHandler
    )


    print(
        "Web UI запущен: "
        "http://localhost:8000/login.html"
    )

    print(
        "Inventory API: "
        "http://localhost:8000/api/inventory"
    )

    print(
        "Power On API: "
        "http://localhost:8000/api/power-on"
    )

    print(
        "Journal API: "
        "http://localhost:8000/api/journal"
    )

    print(
        "Для остановки нажмите Ctrl+C"
    )


    try:

        httpd.serve_forever()

    except KeyboardInterrupt:

        print(
            "\nСервер остановлен"
        )

        httpd.server_close()
