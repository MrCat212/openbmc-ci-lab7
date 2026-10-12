pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        OPENBMC_URL   = 'https://127.0.0.1:2443'
        WEB_UI_URL    = 'http://127.0.0.1:8000'
        HEADLESS      = '1'
        FIREFOX_BINARY = '/usr/bin/firefox-esr'
    }

    stages {
        // 1. Подготавливаем Python, pytest и Selenium.
        stage('Prepare Environment') {
            steps {
                sh '''
                    set -eu
                    rm -rf artifacts .venv
                    mkdir -p artifacts

                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r api_tests/requirements.txt -r webui_tests/requirements.txt

                    {
                        echo '=== CI environment ==='
                        python3 --version
                        pip --version
                        qemu-system-arm --version | head -n 1
                        firefox-esr --version
                        echo '=== Installed Python packages ==='
                        pip freeze
                    } > artifacts/environment.txt 2>&1

                    cat artifacts/environment.txt
                '''
                archiveArtifacts artifacts: 'artifacts/environment.txt'
            }
        }

        // 2. Запускаем OpenBMC Romulus в QEMU.
        stage('Start OpenBMC QEMU') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'openbmc-admin',
                        usernameVariable: 'OPENBMC_USERNAME',
                        passwordVariable: 'OPENBMC_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu
                        IMAGE=$(find /opt/openbmc -maxdepth 1 -type f -name '*.static.mtd' | sort | tail -n 1)

                        if [ -z "$IMAGE" ]; then
                            echo 'ERROR: OpenBMC MTD image not found in /opt/openbmc'
                            exit 1
                        fi

                        echo "Using image: $IMAGE"
                        cp "$IMAGE" ci-openbmc.mtd

                        JENKINS_NODE_COOKIE=dontKillMe nohup qemu-system-arm \
                            -m 256 \
                            -M romulus-bmc \
                            -nographic \
                            -drive file=ci-openbmc.mtd,format=raw,if=mtd \
                            -net nic \
                            -net user,hostfwd=tcp:0.0.0.0:2222-:22,hostfwd=tcp:0.0.0.0:2443-:443,hostfwd=udp:0.0.0.0:2623-:623,hostname=qemu \
                            > artifacts/qemu.log 2>&1 &

                        echo $! > qemu.pid
                        echo "QEMU PID: $(cat qemu.pid)"
                        echo 'Waiting for OpenBMC Redfish...'

                        READY=0
                        i=1
                        while [ "$i" -le 150 ]; do
                            if curl -skf --max-time 5 \
                                -u "$OPENBMC_USERNAME:$OPENBMC_PASSWORD" \
                                "$OPENBMC_URL/redfish/v1/" > /dev/null; then
                                READY=1
                                break
                            fi
                            echo "Attempt $i: OpenBMC is not ready yet"
                            sleep 2
                            i=$((i + 1))
                        done

                        if [ "$READY" -ne 1 ]; then
                            echo 'ERROR: OpenBMC did not become ready'
                            tail -n 80 artifacts/qemu.log || true
                            exit 1
                        fi

                        {
                            echo 'OpenBMC successfully started'
                            echo "QEMU PID: $(cat qemu.pid)"
                            echo "Redfish URL: $OPENBMC_URL/redfish/v1/"
                            echo "Image: $IMAGE"
                        } > artifacts/qemu_start_report.txt

                        cat artifacts/qemu_start_report.txt
                    '''
                    archiveArtifacts artifacts: 'artifacts/qemu_start_report.txt,artifacts/qemu.log'
                }
            }
        }

        // 3. Проверяем Redfish API с помощью pytest.
        stage('Redfish API Tests') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'openbmc-admin',
                        usernameVariable: 'REDFISH_USERNAME',
                        passwordVariable: 'REDFISH_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu
                        . .venv/bin/activate
                        export REDFISH_URL="$OPENBMC_URL"

                        set +e
                        pytest -v api_tests/tests \
                            --junitxml=artifacts/api_tests.xml \
                            > artifacts/api_tests.txt 2>&1
                        RESULT=$?
                        set -e

                        cat artifacts/api_tests.txt
                        exit "$RESULT"
                    '''
                    archiveArtifacts artifacts: 'artifacts/api_tests.txt,artifacts/api_tests.xml'
                }
            }
        }

        // 4. Запускаем наш учебный WebUI-сервер для Selenium.
        stage('Start WebUI') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'openbmc-admin',
                        usernameVariable: 'OPENBMC_USERNAME',
                        passwordVariable: 'OPENBMC_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu
                        . .venv/bin/activate

                        JENKINS_NODE_COOKIE=dontKillMe nohup sh -c '
                            cd webui_tests
                            exec ../.venv/bin/python server.py
                        ' > artifacts/webui_server.log 2>&1 &

                        echo $! > webui.pid
                        echo "WebUI server PID: $(cat webui.pid)"

                        READY=0
                        i=1
                        while [ "$i" -le 30 ]; do
                            if curl -sf --max-time 5 "$WEB_UI_URL/login.html" > /dev/null; then
                                READY=1
                                break
                            fi
                            echo "Attempt $i: WebUI is not ready yet"
                            sleep 1
                            i=$((i + 1))
                        done

                        if [ "$READY" -ne 1 ]; then
                            echo 'ERROR: WebUI did not become ready'
                            cat artifacts/webui_server.log || true
                            exit 1
                        fi

                        {
                            echo 'WebUI successfully started'
                            echo "URL: $WEB_UI_URL/login.html"
                            echo "PID: $(cat webui.pid)"
                        } > artifacts/webui_start_report.txt

                        cat artifacts/webui_start_report.txt
                    '''
                    archiveArtifacts artifacts: 'artifacts/webui_start_report.txt,artifacts/webui_server.log'
                }
            }
        }

        // 5. Подготавливаем пользователя и запускаем Selenium-тесты.
        stage('OpenBMC WebUI Tests') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'openbmc-admin',
                        usernameVariable: 'OPENBMC_USERNAME',
                        passwordVariable: 'OPENBMC_PASSWORD'
                    ),
                    usernamePassword(
                        credentialsId: 'openbmc-test-user',
                        usernameVariable: 'WEBUI_USERNAME',
                        passwordVariable: 'WEBUI_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu
                        . .venv/bin/activate

                        export TEST_USERNAME="$WEBUI_USERNAME"
                        export TEST_PASSWORD="$WEBUI_PASSWORD"
                        export MOZ_DISABLE_CONTENT_SANDBOX=1

                        echo 'Preparing Selenium test account...'
                        if ! python scripts/prepare_test_account.py \
                            > artifacts/account_prepare.txt 2>&1; then
                            cat artifacts/account_prepare.txt
                            exit 1
                        fi
                        cat artifacts/account_prepare.txt

                        set +e
                        python webui_tests/openbmc_auth_tests.py \
                            > artifacts/webui_tests.txt 2>&1
                        RESULT=$?
                        set -e

                        cat artifacts/webui_tests.txt
                        exit "$RESULT"
                    '''
                    archiveArtifacts artifacts: 'artifacts/webui_tests.txt,artifacts/account_prepare.txt'
                }
            }
        }

        // 6. Нагрузочный тест Redfish API: допускаем разный размер JSON,
        // но реально неуспешные запросы и ответы HTTP != 2xx проваливают сборку.
        stage('Load Test') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'openbmc-admin',
                        usernameVariable: 'OPENBMC_USERNAME',
                        passwordVariable: 'OPENBMC_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu

                        # -l: Redfish JSON может менять размер между запросами.
                        # Ошибки подключения и HTTP-ошибки всё равно проверяем.
                        if ab -l -n 50 -c 5 \
                            -A "$OPENBMC_USERNAME:$OPENBMC_PASSWORD" \
                            "$OPENBMC_URL/redfish/v1/Systems/system" \
                            > artifacts/load_test.txt 2>&1; then
                            :
                        else
                            cat artifacts/load_test.txt
                            echo 'ERROR: ApacheBench exited with an error'
                            exit 1
                        fi

                        cat artifacts/load_test.txt

                        # ApacheBench может завершиться с кодом 0 даже при
                        # Failed requests > 0. Поэтому проверяем его отчёт.
                        awk '
                            /^Complete requests:/ { complete = $3 }
                            /^Failed requests:/ { failed = $3 }
                            /^Non-2xx responses:/ { non2xx = $3 }
                            END {
                                if (complete != 50) {
                                    print "FAIL: expected 50 requests, got " complete
                                    exit 1
                                }
                                if (failed != 0) {
                                    print "FAIL: ApacheBench reports " failed " failed requests"
                                    exit 1
                                }
                                if (non2xx != 0) {
                                    print "FAIL: ApacheBench reports " non2xx " non-2xx responses"
                                    exit 1
                                }
                                print "PASS: 50 requests completed; no failed requests or non-2xx responses"
                            }
                        ' artifacts/load_test.txt
                    '''
                    archiveArtifacts artifacts: 'artifacts/load_test.txt'
                }
            }
        }
    }

    post {
        always {
            sh '''
                echo 'Stopping background services...'
                if [ -f webui.pid ]; then
                    kill "$(cat webui.pid)" 2>/dev/null || true
                    rm -f webui.pid
                fi
                if [ -f qemu.pid ]; then
                    kill "$(cat qemu.pid)" 2>/dev/null || true
                    rm -f qemu.pid
                fi
                sleep 2
            '''
            archiveArtifacts artifacts: 'artifacts/**/*', allowEmptyArchive: true
        }
        success {
            echo 'CI/CD Pipeline completed successfully.'
        }
        failure {
            echo 'CI/CD Pipeline failed. Check stage reports and artifacts.'
        }
    }
}
