pipeline {
    agent none

    environment {
        // Używamy zmiennej globalnej dla rejestru, łatwej do zmiany
        REGISTRY_URL = "docker.io/youruser" 
        // Tagujemy obrazy unikalnym ID builda dla lepszego śledzenia
        IMAGE_TAG = env.BUILD_NUMBER
    }

    stages {
        stage('Checkout') {
            agent any
            steps {
                checkout scm
                stash name: 'source', includes: '**/*'
            }
        }

        stage('Run Tests') {
            // Uruchamiamy wszystkie testy równolegle, aby skrócić czas
            parallel {
                stage('Test Python') {
                    agent {
                        // ZMIANA: Używamy oficjalnego obrazu Pythona
                        docker { image 'python:3.11-slim' }
                    }
                    steps {
                        unstash 'source'
                        // ZMIANA: Instalujemy uv i zależności
                        sh 'pip install --no-cache-dir uv'
                        sh 'uv sync --all-extras --frozen'
                        sh '''
                            uv run ruff check src
                            uv run mypy src
                            uv run pytest --cov=src --cov-report=xml
                        '''
                        stash name: 'coverage', includes: 'coverage.xml'
                    }
                }
                stage('Test Java') {
                    agent {
                        // ZMIANA: Używamy obrazu Gradle z JDK 21
                        docker { image 'gradle:jdk21' }
                    }
                    steps {
                        unstash 'source'
                        sh 'cd services/ticket-adapter-java && gradle test'
                    }
                }
                stage('Test Node.js') {
                    agent {
                        // Używamy obrazu Node.js zgodnego z projektem
                        docker { image 'node:22-alpine' }
                    }
                    steps {
                        unstash 'source'
                        sh 'cd services/admin-portal && npm ci && npm test'
                    }
                }
            }
        }

        stage('Build & Push All Images') {
            agent { docker { image 'docker:25' } }
            steps {
                unstash 'source'
                script {
                    withDockerRegistry(credentialsId: 'docker-credentials', url: "https://${REGISTRY_URL}") {
                        // Budujemy wszystkie obrazy
                        sh "docker build -t ${REGISTRY_URL}/astradesk-api:${IMAGE_TAG} ."
                        sh "docker build -t ${REGISTRY_URL}/astradesk-ticket:${IMAGE_TAG} services/ticket-adapter-java"
                        sh "docker build -t ${REGISTRY_URL}/astradesk-admin:${IMAGE_TAG} services/admin-portal"
                        sh "docker build -t ${REGISTRY_URL}/astradesk-auditor:${IMAGE_TAG} services/auditor"

                        // Wysyłamy wszystkie obrazy
                        sh "docker push ${REGISTRY_URL}/astradesk-api:${IMAGE_TAG}"
                        sh "docker push ${REGISTRY_URL}/astradesk-ticket:${IMAGE_TAG}"
                        sh "docker push ${REGISTRY_URL}/astradesk-admin:${IMAGE_TAG}"
                        sh "docker push ${REGISTRY_URL}/astradesk-auditor:${IMAGE_TAG}"
                    }
                }
            }
            
        }

        stage('Build Java Packs') {
            sh './gradlew build'
        }

        stage('Test Python Packs') { 
            sh 'uv run pytest packages/domain-finance/tests'
            sh 'uv run pytest packages/domain-supply/tests' 
        }

        stage('Deploy to Kubernetes') {
            agent { docker { image 'alpine/helm:3.15.3' } }
            steps {
                unstash 'source'
                // Tutaj powinny być wstrzyknięte credentials do klastra K8s
                sh '''
                    helm upgrade --install astradesk deploy/chart \\
                        --set api.image.repository=${REGISTRY_URL}/astradesk-api \\
                        --set api.image.tag=${IMAGE_TAG} \\
                        --set admin.image.repository=${REGISTRY_URL}/astradesk-admin \\
                        --set admin.image.tag=${IMAGE_TAG} \\
                        --set ticketAdapter.image.repository=${REGISTRY_URL}/astradesk-ticket \\
                        --set ticketAdapter.image.tag=${IMAGE_TAG} \\
                        --set auditor.image.repository=${REGISTRY_URL}/astradesk-auditor \\
                        --set auditor.image.tag=${IMAGE_TAG} \\
                        --namespace astradesk \\
                        --create-namespace \\
                        --wait --timeout 5m
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
            junit '**/build/test-results/test/TEST-*.xml' // Zbieranie wyników testów Javy
        }
    }
}
