pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        OPENBMC_URL = 'https://127.0.0.1:2443'
        WEB_UI_URL = 'http://127.0.0.1:8000'

        HEADLESS = '1'
        FIREFOX_BINARY = '/usr/bin/firefox-esr'

        WRONG_PASSWORD = 'WrongPass123!'
        PYTHONUNBUFFERED = '1'
    }

    stages {

        // ====================================================
        // ПОДГОТОВКА ОКРУЖЕНИЯ
        // ====================================================

        stage('Prepare Environment') {
            steps {
                sh '''
                    set -eu

                    rm -rf artifacts .venv
                    mkdir -p artifacts

                    python3 -m venv .venv

                    . .venv/bin/activate

                    python -m pip install --upgrade pip

                    pip install \
                        -r api_tests/requirements.txt \
                        -r webui_tests/requirements.txt

                    {
                        echo "=== CI environment ==="
                        echo
                        python3 --version
                        echo
                        pip --version
                        echo
                        qemu-system-arm --version | head -n 1
                        echo
                        firefox-esr --version
                        echo
                        echo "Installed Python packages:"
                        pip freeze
                    } > artifacts/environment.txt

                    cat artifacts/environment.txt
                '''

                archiveArtifacts(
                    artifacts: 'artifacts/environment.txt'
                )
            }
        }


        // ====================================================
        // ЗАПУСК QEMU + OPENBMC
        // ====================================================

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

                        IMAGE=$(find /opt/openbmc \
                            -maxdepth 1 \
                            -type f \
                            -name "*.static.mtd" \
                            | sort \
                            | tail -n 1)

                        if [ -z "$IMAGE" ]; then
                            echo "OpenBMC image not found"
                            exit 1
                        fi

                        echo "Using image: $IMAGE"

                        # Работаем с копией, чтобы исходный образ не портить.
                        cp "$IMAGE" ci-openbmc.mtd

                        JENKINS_NODE_COOKIE=dontKillMe \
                        nohup qemu-system-arm \
                            -m 256 \
                            -M romulus-bmc \
                            -nographic \
                            -drive file=ci-openbmc.mtd,format=raw,if=mtd \
                            -net nic \
                            -net user,hostfwd=tcp:0.0.0.0:2222-:22,hostfwd=tcp:0.0.0.0:2443-:443,hostfwd=udp:0.0.0.0:2623-:623,hostname=qemu \
                            > artifacts/qemu.log 2>&1 &

                        echo $! > qemu.pid

                        echo "QEMU PID: $(cat qemu.pid)"

                        echo "Waiting for OpenBMC Redfish..."

                        READY=0

                        i=1

                        while [ "$i" -le 90 ]; do

                            if curl \
                                -sk \
                                -u "$OPENBMC_USERNAME:$OPENBMC_PASSWORD" \
                                "$OPENBMC_URL/redfish/v1/" \
                                > artifacts/redfish_root.json
                            then
                                READY=1
                                break
                            fi

                            echo "Attempt $i: OpenBMC is not ready yet"

                            sleep 2

                            i=$((i + 1))
                        done

                        if [ "$READY" -ne 1 ]; then
                            echo "OpenBMC did not start"
                            tail -n 100 artifacts/qemu.log || true
                            exit 1
                        fi

                        {
                            echo "OpenBMC successfully started"
                            echo "QEMU PID: $(cat qemu.pid)"
                            echo "Redfish URL: $OPENBMC_URL/redfish/v1/"
                            echo "Image: $IMAGE"
                        } > artifacts/qemu_start_report.txt

                        cat artifacts/qemu_start_report.txt
                    '''

                    archiveArtifacts(
                        artifacts: 'artifacts/qemu_start_report.txt,artifacts/redfish_root.json'
                    )
                }
            }
        }


        // ====================================================
        // API TESTS — ЛАБОРАТОРНАЯ №5
        // ====================================================

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
                        . .venv/bin/activate

                        export REDFISH_URL="$OPENBMC_URL"

                        set +e

                        pytest \
                            -v \
                            api_tests/tests \
                            --junitxml=artifacts/api_tests.xml \
                            > artifacts/api_tests.txt 2>&1

                        RESULT=$?

                        set -e

                        cat artifacts/api_tests.txt

                        exit "$RESULT"
                    '''

                    archiveArtifacts(
                        artifacts: 'artifacts/api_tests.txt,artifacts/api_tests.xml'
                    )
                }
            }
        }


        // ====================================================
        // ЗАПУСК ЛОКАЛЬНОГО WEB UI
        // ====================================================

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

                        export OPENBMC_URL="$OPENBMC_URL"

                        JENKINS_NODE_COOKIE=dontKillMe \
                        nohup sh -c '
                            cd webui_tests
                            exec ../.venv/bin/python server.py
                        ' > artifacts/webui_server.log 2>&1 &

                        echo $! > webui.pid

                        echo "WebUI server PID: $(cat webui.pid)"

                        READY=0

                        i=1

                        while [ "$i" -le 30 ]; do

                            if curl \
                                -s \
                                "$WEB_UI_URL/login.html" \
                                > /dev/null
                            then
                                READY=1
                                break
                            fi

                            echo "Attempt $i: WebUI is not ready yet"

                            sleep 1

                            i=$((i + 1))
                        done

                        if [ "$READY" -ne 1 ]; then
                            echo "WebUI server did not start"
                            cat artifacts/webui_server.log || true
                            exit 1
                        fi

                        {
                            echo "WebUI successfully started"
                            echo "URL: $WEB_UI_URL/login.html"
                            echo "PID: $(cat webui.pid)"
                        } > artifacts/webui_start_report.txt

                        cat artifacts/webui_start_report.txt
                    '''

                    archiveArtifacts(
                        artifacts: 'artifacts/webui_start_report.txt'
                    )
                }
            }
        }


        // ====================================================
        // SELENIUM WEB UI TESTS — ЛАБОРАТОРНАЯ №4
        // ====================================================

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

                        export OPENBMC_URL="$OPENBMC_URL"
                        export TEST_USERNAME="$WEBUI_USERNAME"
                        export TEST_PASSWORD="$WEBUI_PASSWORD"
                        export WEB_UI_URL="$WEB_UI_URL"
                        export HEADLESS="$HEADLESS"
                        export FIREFOX_BINARY="$FIREFOX_BINARY"

                        # Если предыдущий запуск оставил тестовую
                        # учётную запись заблокированной — разблокируем.
                        curl \
                            -sk \
                            -u "$OPENBMC_USERNAME:$OPENBMC_PASSWORD" \
                            -X PATCH \
                            -H "Content-Type: application/json" \
                            -d '{"Locked": false}' \
                            "$OPENBMC_URL/redfish/v1/AccountService/Accounts/$WEBUI_USERNAME" \
                            > artifacts/account_unlock.json \
                            || true

                        set +e

                        python \
                            webui_tests/openbmc_auth_tests.py \
                            > artifacts/webui_tests.txt 2>&1

                        RESULT=$?

                        set -e

                        cat artifacts/webui_tests.txt

                        exit "$RESULT"
                    '''

                    archiveArtifacts(
                        artifacts: 'artifacts/webui_tests.txt,artifacts/account_unlock.json'
                    )
                }
            }
        }


        // ====================================================
        // НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ
        // ====================================================

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
                        set +e

                        ab \
                            -n 50 \
                            -c 5 \
                            -A "$OPENBMC_USERNAME:$OPENBMC_PASSWORD" \
                            "$OPENBMC_URL/redfish/v1/Systems/system" \
                            > artifacts/load_test.txt 2>&1

                        RESULT=$?

                        set -e

                        cat artifacts/load_test.txt

                        exit "$RESULT"
                    '''

                    archiveArtifacts(
                        artifacts: 'artifacts/load_test.txt'
                    )
                }
            }
        }
    }


    // ========================================================
    // ЗАВЕРШЕНИЕ PIPELINE
    // ========================================================

    post {

        always {

            sh '''
                echo "Stopping background services..."

                if [ -f webui.pid ]; then
                    kill "$(cat webui.pid)" 2>/dev/null || true
                fi

                if [ -f qemu.pid ]; then
                    kill "$(cat qemu.pid)" 2>/dev/null || true
                fi

                sleep 2
            '''

            archiveArtifacts(
                artifacts: 'artifacts/**/*',
                allowEmptyArchive: true
            )
        }

        success {
            echo 'CI/CD Pipeline completed successfully.'
        }

        failure {
            echo 'CI/CD Pipeline failed. Check stage reports and artifacts.'
        }
    }
}
