pipeline {
  agent any
  environment {
    REGISTRY = "docker.io/youruser"
    API_IMAGE = "${REGISTRY}/astradesk-api"
    TICKET_IMAGE = "${REGISTRY}/astradesk-ticket"
    ADMIN_IMAGE = "${REGISTRY}/astradesk-admin"
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Python build & test') {
      steps {
        sh 'pip install uv && uv sync --frozen'
        sh 'uv run ruff check src && uv run mypy src && uv run pytest -q'
        sh 'docker build -t $API_IMAGE:$BUILD_NUMBER .'
      }
    }
    stage('Java build') {
      steps {
        sh 'docker build -t $TICKET_IMAGE:$BUILD_NUMBER services/ticket-adapter-java'
      }
    }
    stage('Node build') {
      steps {
        sh 'docker build -t $ADMIN_IMAGE:$BUILD_NUMBER services/admin-portal'
      }
    }
    stage('Push images') {
      steps { sh 'docker push $API_IMAGE:$BUILD_NUMBER && docker push $TICKET_IMAGE:$BUILD_NUMBER && docker push $ADMIN_IMAGE:$BUILD_NUMBER' }
    }
    stage('Helm deploy') {
      steps {
        sh 'helm upgrade --install astradesk deploy/chart --set image.repository=$API_IMAGE --set image.tag=$BUILD_NUMBER'
      }
    }
  }
}
