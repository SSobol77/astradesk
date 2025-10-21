// Jenkinsfile (Wersja Produkcyjna)

pipeline {
    agent none

    environment {
        REGISTRY_URL = "docker.io/youruser"
        // Użyłem skrótu z commita jako tagu
        IMAGE_TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
    }

    stages {
        stage('Checkout') {
            agent any
            steps {
                checkout scm
                stash name: 'source', includes: '**/*'
            }
        }

        stage('Code Analysis & Tests') {
            // Uruchamiamy wszystkie testy i analizy równolegle
            parallel {
                stage('Analyze & Test Python') {
                    agent { docker { image 'python:3.11-slim' } }
                    steps {
                        unstash 'source'
                        // Używamy cache dla .venv
                        cache(path: '.venv', key: "venv-py-${checksum 'uv.lock'}") {
                            sh 'pip install --no-cache-dir uv'
                            sh 'uv sync --all-extras --frozen'
                        }
                        sh 'uv sync --all-extras --frozen'
                        sh 'uv run ruff check .'
                        sh 'uv run mypy .'
                        sh 'uv run pytest --cov --cov-report=xml'
                        stash name: 'coverage-py', includes: 'coverage.xml'
                    }
                }
                stage('Analyze & Test Java') {
                    agent { docker { image 'gradle:jdk21' } }
                    steps {
                        unstash 'source'
                        // Używamy cache dla zależności Gradle
                        cache(path: '.gradle/caches', key: "gradle-caches-${checksum '**/*.gradle.kts'}") {
                            // Uruchamiamy `check`, które zawiera `test` i lintery (Checkstyle)
                            sh './gradlew check'
                        }
                    }
                }
                stage('Analyze & Test Node.js') {
                    agent { docker { image 'node:22-alpine' } }
                    steps {
                        unstash 'source'
                        // Cache: Używamy cache dla node_modules
                        cache(path: 'services/admin-portal/node_modules', key: "npm-modules-${checksum 'services/admin-portal/package-lock.json'}") {
                            sh 'cd services/admin-portal && npm ci'
                        }
                        // Linter: Dodajemy linter (jeśli skonfigurowany w package.json)
                        sh 'cd services/admin-portal && npm run lint && npm test'
                    }
                }
            }
        }

        stage('Build & Push Docker Images') {
            agent { docker { image 'docker:25' } }
            steps {
                unstash 'source'
                script {
                    withDockerRegistry(credentialsId: 'docker-credentials', url: "https://index.docker.io/v1/") {
                        // Budujemy i wysyłamy wszystkie obrazy
                        def images = [
                            "api": ".",
                            "ticket": "services/ticket-adapter-java",
                            "admin": "services/admin-portal",
                            "auditor": "services/auditor"
                        ]
                        images.each { name, path ->
                            def imageName = "${REGISTRY_URL}/astradesk-${name}:${IMAGE_TAG}"
                            sh "docker build -t ${imageName} ${path}"
                            sh "docker push ${imageName}"
                        }
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            agent { docker { image 'alpine/helm:3.15.3' } }
            // Uwaga: Dodalem tu warunek `when`, aby deploy był uruchamiany tylko dla gałęzi `main`
            when { branch 'main' }
            steps {
                unstash 'source'
                // Tutaj powinny być wstrzyknięte credentials do klastra K8s
                sh """
                    helm upgrade --install astradesk deploy/chart \\
                        --set api.image.repository=${REGISTRY_URL}/astradesk-api \\
                        --set api.image.tag=${IMAGE_TAG} \\
                        --set admin.image.repository=${REGISTRY_URL}/astradesk-admin \\
                        --set admin.image.tag=${IMAGE_TAG} \\
                        --set ticketAdapter.image.repository=${REGISTRY_URL}/astradesk-ticket \\
                        --set ticketAdapter.image.tag=${IMAGE_TAG} \\
                        --set auditor.image.repository=${REGISTRY_URL}/astradesk-auditor \\
                        --set auditor.image.tag=${IMAGE_TAG} \\
                        --namespace astradesk-prod \\
                        --create-namespace \\
                        --wait --timeout 5m
                """
            }
        }
    }

    post {
        always {
            // Zbieranie artefaktów
            archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
            junit '**/build/test-results/test/TEST-*.xml'
        }
    }
}
