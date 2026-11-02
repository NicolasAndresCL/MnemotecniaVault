// Mnemotecnia Vault — pipeline declarativo para el Jenkins local (C:\dev\projects\jenkins).
// Mismo filtro que .github/workflows/ci.yml: lint -> tests (SQLite + Postgres 18) -> build + smoke.
//
// Hecho para ese controller tal como está (patrón de CmdVault): cliente docker con el socket del host
// montado y SIN el plugin Docker Pipeline. Cada paso corre en un contenedor efímero con
// `docker run --rm --volumes-from`: JENKINS_HOME es un volumen nombrado y el workspace no existe en el
// host, así que el contenedor del paso hereda los volúmenes del controller y ve la misma ruta.
// No usa credenciales: los secretos del stack de prueba son efímeros (openssl rand).

def stageFallido = ''

// Ejecuta `comando` (sh -e) en un contenedor efímero que comparte el workspace del controller.
// `comando` no debe contener comillas simples.
def enContenedor(String imagen, String comando, String extra = '') {
    sh """docker run --rm --volumes-from "\$(hostname)" -w "\$WORKSPACE" -e HOME="\$WORKSPACE" \
        -e PIP_NO_CACHE_DIR=1 -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PYTHONIOENCODING=utf-8 \
        ${extra} ${imagen} sh -ec '${comando}'"""
}

pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        PY_IMG = 'python:3.14-slim'
        // Único por job + rama + build (Compose exige [a-z0-9_-]).
        CI_ID = "ci-${env.JOB_NAME}-${env.BUILD_NUMBER}".toLowerCase().replaceAll('[^a-z0-9]+', '-')
        RED_PG = "${env.CI_ID}-net"
        PG = "${env.CI_ID}-pg"
    }

    stages {
        stage('Lint') {
            steps {
                script {
                    stageFallido = env.STAGE_NAME
                    enContenedor(env.PY_IMG, '''
                        python -m venv .venv-lint
                        .venv-lint/bin/pip install -q ruff==0.17.1
                        .venv-lint/bin/ruff check .
                        .venv-lint/bin/ruff format --check .
                    ''')
                    sh '''
                        docker run --rm -i hadolint/hadolint < Dockerfile
                        POSTGRES_PASSWORD=ci STORAGE_SECRET=ci docker compose config --quiet
                    '''
                    enContenedor('alpine/k8s:1.34.1', '''
                        kubectl kustomize k8s > /tmp/k8s.yaml
                        kubeconform -strict -summary /tmp/k8s.yaml
                    ''')
                }
            }
        }

        stage('Tests') {
            parallel {
                stage('SQLite') {
                    steps {
                        script {
                            stageFallido = env.STAGE_NAME
                            enContenedor(env.PY_IMG, '''
                                python -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt
                                .venv/bin/pytest -rs --cov --cov-fail-under=90 --junitxml=reports/sqlite.xml
                            ''')
                        }
                    }
                    post { always { junit allowEmptyResults: true, testResults: 'reports/sqlite.xml' } }
                }
                stage('Postgres 18') {
                    steps {
                        script {
                            stageFallido = env.STAGE_NAME
                            // Sidecar efímero en una red propia del build; se elimina en post.
                            sh '''
                                docker network create "$RED_PG"
                                docker run -d --rm --name "$PG" --network "$RED_PG" --network-alias pg \
                                    -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=app_test postgres:18-alpine
                                until docker exec "$PG" pg_isready -U app -d app_test; do sleep 1; done
                            '''
                            enContenedor(env.PY_IMG, '''
                                python -m venv .venv-pg && .venv-pg/bin/pip install -q -r requirements-dev.txt
                                .venv-pg/bin/pytest -rs -p no:cacheprovider
                            ''', "--network ${env.RED_PG} -e TEST_DATABASE_URL=postgresql+psycopg://app:app@pg:5432/app_test")
                        }
                    }
                    post {
                        always { sh 'docker rm -f "$PG" >/dev/null 2>&1 || true; docker network rm "$RED_PG" >/dev/null 2>&1 || true' }
                    }
                }
            }
        }

        stage('Build + smoke') {
            environment {
                // Proyecto y puerto propios por build: no choca con el stack diario ni con el 8080 de Jenkins.
                COMPOSE_PROJECT_NAME = "${env.CI_ID}"
                APP_PORT = '28095'
                IMPORT_ON_STARTUP = 'false'
            }
            steps {
                script { stageFallido = env.STAGE_NAME }
                sh '''
                    export POSTGRES_PASSWORD=$(openssl rand -hex 16)
                    export STORAGE_SECRET=$(openssl rand -hex 24)
                    docker compose up -d --build --wait --wait-timeout 180
                '''
                // El smoke corre en la red del stack: desde el controller, "localhost" no es el host.
                enContenedor(env.PY_IMG, '''
                    apt-get update -qq && apt-get install -y -qq curl >/dev/null
                    bash scripts/smoke.sh http://app:8080
                ''', "--network ${env.COMPOSE_PROJECT_NAME}_default")
            }
            post {
                failure { sh 'docker compose logs --no-color --tail=200 || true' }
                // Norma: lo que se levanta para probar, se baja SIEMPRE.
                always { sh 'docker compose down -v --remove-orphans || true' }
            }
        }
    }

    post {
        failure { echo "Falló el stage: ${stageFallido}" }
        success { echo 'Pipeline en verde.' }
    }
}
