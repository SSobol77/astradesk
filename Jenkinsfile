pipeline {
  agent none
  environment {
    REGISTRY = "docker.io/youruser"
    API_IMAGE = "${REGISTRY}/astradesk-api"
    TICKET_IMAGE = "${REGISTRY}/astradesk-ticket"
    ADMIN_IMAGE = "${REGISTRY}/astradesk-admin"
    UV_VERSION = "0.4.22"
    PYTHON_VERSION = "3.11.8"
    UV_EXTRA_INDEX_URL = "https://download.pytorch.org/whl/cu121"
    UV_INDEX_STRATEGY = "unsafe-best-match"
  }
  stages {
    stage('Checkout') {
      agent { docker { image "ghcr.io/astral-sh/uv:${UV_VERSION}-py${PYTHON_VERSION}" } }
      steps {
        checkout scm
        stash name: 'source', includes: '**/*'
      }
    }
    stage('Python build & test') {
      agent { docker { image "ghcr.io/astral-sh/uv:${UV_VERSION}-py${PYTHON_VERSION}" } }
      steps {
        unstash 'source'
        cache(path: '.venv', key: "venv-${env.BUILD_NUMBER}-${env.GIT_COMMIT}") {
          sh 'uv sync --all-extras --frozen'
        }
        sh '''
          uv run ruff check src
          uv run ruff format --check src
          uv run mypy src
          uv run pytest --cov=src --cov-report=xml --cov-report=term-missing -q
        '''
        stash name: 'coverage', includes: 'coverage.xml'
        script {
          withDockerRegistry(credentialsId: 'docker-credentials', url: 'https://docker.io') {
            sh 'docker build -t $API_IMAGE:$BUILD_NUMBER .'
          }
        }
      }
    }
    stage('Java build') {
      agent { docker { image 'maven:3.9.9-eclipse-temurin-17' } }
      steps {
        unstash 'source'
        script {
          withDockerRegistry(credentialsId: 'docker-credentials', url: 'https://docker.io') {
            sh 'docker build -t $TICKET_IMAGE:$BUILD_NUMBER services/ticket-adapter-java'
          }
        }
      }
    }
    stage('Node build') {
      agent { docker { image 'node:20' } }
      steps {
        unstash 'source'
        script {
          withDockerRegistry(credentialsId: 'docker-credentials', url: 'https://docker.io') {
            sh 'docker build -t $ADMIN_IMAGE:$BUILD_NUMBER services/admin-portal'
          }
        }
      }
    }
    stage('Push images') {
      agent { docker { image 'docker:25' } }
      steps {
        unstash 'source'
        script {
          withDockerRegistry(credentialsId: 'docker-credentials', url: 'https://docker.io') {
            sh '''
              docker push $API_IMAGE:$BUILD_NUMBER
              docker push $TICKET_IMAGE:$BUILD_NUMBER
              docker push $ADMIN_IMAGE:$BUILD_NUMBER
            '''
          }
        }
      }
    }
    stage('Helm deploy') {
      agent { docker { image 'alpine/helm:3.15.3' } }
      steps {
        unstash 'source'
        sh '''
          helm upgrade --install astradesk deploy/chart \
            --set image.repository=$API_IMAGE \
            --set image.tag=$BUILD_NUMBER \
            --namespace astradesk \
            --create-namespace \
            --wait --timeout 5m
        '''
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
    }
  }
}
