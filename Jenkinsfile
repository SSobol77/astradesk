//SPDX-License-Identifier: Apache-2.0
// File: Jenkinsfile v2.1 --production-ready--
// Project: AstraDesk Enterprise AI Agents Framework
// Description:
//     Full production Jenkins pipeline for AstraDesk.
//     Covers:
//       • Checkout & stash
//       • Parallel code-analysis + unit/integration tests (Python 3.14, Java 25, Node 22)
//       • Coverage aggregation & SonarQube scan
//       • Secrets injection into Admin API (/secrets)
//       • Terraform (init → validate → plan → apply) with AWS credentials
//       • Config-management dry-run & full deploy(Ansible / Puppet / Salt)
//       • Docker multi-arch build + push (with cache, Sigstore signing)
//       • Istio mTLS STRICT verification + cert-manager secrets sync
//       • Helm chart lint → test → upgrade (autoscaling, DB endpoints from TF)
//       • Post-runartifactarchiving, JUnit reports, Slack notifications
//     All stages are idempotent, retry-aware and use explicit credential IDs.
// Author: Siergej Sobolewski
// Since: 2025-11-09

pipeline {
    agent none

    // --------------------------------------------------------------------- //
// Global environment (change only REGISTRY_URL / credential IDs)
    // --------------------------------------------------------------------- //
    environment {
        // Docker
        REGISTRY_URL          = 'docker.io/youruser'                     // <-- change
        IMAGE_TAG             = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()

        // Kubernetes / Helm
        KUBE_CREDENTIALS_ID   = 'kubeconfig-astradesk'                  // kubeconfig file
        HELM_NAMESPACE        = 'astradesk-prod'

        // AWS / Terraform
        AWS_CREDENTIALS_ID    = 'aws-credentials'// AWS access/secret keys
        TERRAFORM_DIR         = 'infra'
        TF_VAR_FILE           = "${TERRAFORM_DIR}/terraform.tfvars"

        // Admin API (JWT + endpoint)
        ADMIN_API_JWT_ID      = 'admin-api-jwt'                         // plain string JWT
        ADMIN_API_URL         = 'http://localhost:8080/api/admin/v1'    // reachable from agents

        // Config-management
        ANSIBLE_INVENTORY     = 'ansible/inventories/prod/hosts.ini'
        PUPPET_MANIFEST       = 'puppet/manifests/astradesk.pp'
        SALT_STATE            = 'astradesk'

        // Misc
        SONAR_TOKEN_ID        = 'sonar-token'
        SLACK_CHANNEL         = '#astradesk-ci'
    }

    // --------------------------------------------------------------------- //
    // Pipeline stages
    // --------------------------------------------------------------------- //
    stages {

       //----------------------------------------------------------------- //
        // 1. OpenAPI sync
        // ----------------------------------------------------------------- //
        stage('OpenAPI Sync') {
            steps {
                sh '''
                set -e
                SRC="openapi/astradesk-admin.v1.yaml"
                DST="services/admin-portal/OpenAPI.yaml"
                if [ ! -f "$DST" ] || ! diff -q "$SRC" "$DST" >/dev/null; then
                    echo "[SYNC] Copying $SRC -> $DST"
                    cp "$SRC" "$DST"
                fi
                diff -u "$SRC" "$DST"
                '''
            }
        }

        // ----------------------------------------------------------------- //
        // 2. Checkout & stash source
        // ----------------------------------------------------------------- //
        stage('Checkout') {
            agent any
            steps {
                checkout scm
                stash name: 'source', includes: '**/*', excludes: '**/.git/**'
            }
        }

        //----------------------------------------------------------------- //
        // 3. Parallel code analysis & tests (Python / Java / Node)
        // ----------------------------------------------------------------- //
        stage('Code Analysis & Tests') {
            parallel {

                // --------------------- Python --------------------- //
                stage('Python') {
                    agent { docker { image 'python:3.14-slim' } }
                    environment {
                        UV_CACHE_DIR = '/uv-cache'
                    }
                    steps {
                        unstash 'source'
                        // ---- uv cache mount (Docker BuildKit cache) ---- //
                        cache(path: '.venv', key: "venv-py-${checksum 'uv.lock'}") {
                           sh 'pip install --no-cache-dir uv==0.4.16'
                            sh 'uv sync --all-extras --frozen'
                        }
                        sh 'uv run ruff check .'
                        sh 'uv run mypy .'
                        sh 'uv run pytest --cov --cov-report=xml --junitxml=pytest-report.xml'
                        stash name: 'coverage-py', includes: 'coverage.xml,pytest-report.xml'
                    }
                }

                // --------------------- Java --------------------- //
                stage('Java') {
                    agent { docker { image 'gradle:9.2.0-jdk25'} }
                    steps {
                        unstash 'source'
                        cache(path: '.gradle/caches', key: "gradle-caches-${checksum '**/*.gradle.kts'}") {
                            sh './gradlew check jacocoTestReport'
                        }
                        stash name: 'coverage-java',
                              includes: '**/build/reports/jacoco/test/jacocoTestReport.xml'
                    }
                }

                // --------------------- Node --------------------- //
                stage('Node.js') {
                    agent { docker { image 'node:22-alpine' } }
                    steps {
                        unstash 'source'
                        cache(path: 'services/admin-portal/node_modules',
                              key: "npm-${checksum 'services/admin-portal/package-lock.json'}") {
                            sh 'cd services/admin-portal && npm ci'
                        }
                        sh 'cd services/admin-portal && npm run lint && npm test -- --coverage'
                        stash name: 'coverage-node',
                              includes: 'services/admin-portal/coverage/**'
                    }
                }
                
                // --------------------- MCP --------------------- //
                stage('MCP Gateway') {
                    agent { docker { image 'python:3.14-slim' } }
                    steps {
                        unstash 'source'
                        dir('mcp') {
                            sh 'pip install --no-cache-dir uv==0.4.16'
                            sh 'uv sync'
                            sh 'uv run pytest -v'
                        }
                    }
                }
           }
        }

        // ----------------------------------------------------------------- //
        // 4. Aggregate coverage & SonarQube scan
        // ----------------------------------------------------------------- //
        stage('SonarQube Analysis') {
            agent{ docker { image 'sonarsource/sonar-scanner-cli:latest' } }
            steps {
                unstash 'source'
                unstash 'coverage-py'
               unstash 'coverage-java'
                unstash 'coverage-node'

                withCredentials([string(credentialsId: env.SONAR_TOKEN_ID,variable: 'SONAR_TOKEN')]) {
                    sh '''
                        sonar-scanner \
                          -Dsonar.projectKey=astradesk \
                          -Dsonar.host.url=${SONAR_HOST_URL} \
                          -Dsonar.login=${SONAR_TOKEN} \
                          -Dsonar.sources=. \
                          -Dsonar.python.coverage.reportPaths=coverage.xml \
                          -Dsonar.java.coverage.jacoco.reportPaths=**/build/reports/jacoco/test/jacocoTestReport.xml \
                          -Dsonar.javascript.lcov.reportPaths=services/admin-portal/coverage/lcov.info
                    '''
                }
            }
        }

        // ----------------------------------------------------------------- //
        // 5. Store AWS credentials into Admin API (/secrets)
        // ----------------------------------------------------------------- //
        stage('Store AWSSecrets') {
            agent { docker { image 'curlimages/curl' } }
            steps {
                unstash 'source'
               withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding',
                     credentialsId: env.AWS_CREDENTIALS_ID,
                     accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                     secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
                    string(credentialsId: env.ADMIN_API_JWT_ID, variable: 'JWT')
               ]) {
                    sh '''
                        curl -sSf -X POST "${ADMIN_API_URL}/secrets" \
                          -H "Authorization: Bearer ${JWT}" \
                          -H "Content-Type: application/json" \
                          -d '{
                            "name": "aws_creds",
                            "type": "aws",
                            "access_key": "'"${AWS_ACCESS_KEY_ID}"'",
                            "secret_key": "'"${AWS_SECRET_ACCESS_KEY}"'"
                          }' > aws-secret-response.json
                       cat aws-secret-response.json
                    '''
                    archiveArtifacts artifacts: 'aws-secret-response.json', allowEmptyArchive: true
               }
            }
        }

        // ----------------------------------------------------------------- //
        // 6. Terraform – init + validate
        // ----------------------------------------------------------------- //
        stage('Terraform Init & Validate') {
            agent { docker { image 'hashicorp/terraform:1.9.5' } }   // latest stable 2025
            steps {
                unstash 'source'
                dir(env.TERRAFORM_DIR) {
                    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding',
                                     credentialsId: env.AWS_CREDENTIALS_ID]]) {
                        sh 'terraform init -backend-config="bucket=astradesk-tfstate" -reconfigure'
                        sh 'terraform validate'
                    }
                }
            }
        }

        // ----------------------------------------------------------------- //
        // 7. Terraform – plan (manual approval onnon-main)
        // ----------------------------------------------------------------- //
        stage('Terraform Plan') {
            agent { docker { image 'hashicorp/terraform:1.9.5' } }
            steps {
                unstash 'source'
                dir(env.TERRAFORM_DIR) {
                    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding',
                                      credentialsId: env.AWS_CREDENTIALS_ID]]) {
                        sh 'terraform plan -var-file="${TF_VAR_FILE}" -out=plan.out'
                        archiveArtifacts artifacts: 'plan.out', fingerprint: true
                    }
                }
                stash name: 'tf-plan', includes: "${env.TERRAFORM_DIR}/plan.out"
            }
        }

        // ----------------------------------------------------------------- //
        // 8. Manual approvalfor non-main branches
        // ----------------------------------------------------------------- //
        stage('Approve Terraform') {
            when { not { branch 'main' } }
            steps {
                input message: 'Apply Terraform plan?', ok: 'Apply'
            }
        }

        // ----------------------------------------------------------------- //
        // 9. Terraform –apply (only main or after approval)
        // ----------------------------------------------------------------- //
        stage('Terraform Apply') {
            when {
                anyOf {
                    branch 'main'
                    expression { return env.BRANCH_NAME != 'main' && currentBuild.resultIsBetterOrEqualTo('SUCCESS') }
                }
            }
            agent{ docker { image 'hashicorp/terraform:1.9.5' } }
            steps {
                unstash 'tf-plan'
                dir(env.TERRAFORM_DIR) {
                    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding',
                                      credentialsId: env.AWS_CREDENTIALS_ID]])  {                  
                                        sh 'terraform apply -auto-approve plan.out'
                    }
                }
            }
        }

        // ----------------------------------------------------------------- //
        // 10. Config-management – dry-run (parallel)
        // ----------------------------------------------------------------- //
        stage('Config-Mgmt Dry-Run') {
            parallel {

                stage('Ansible Dry-Run') {
                    agent{ docker { image 'python:3.14-slim' } }
                    steps {
                        unstash 'source'
                        sh 'pip install --no-cache-dir ansible'
                        sh "ansible-playbook -i ${ANSIBLE_INVENTORY} ansible/playbook.yml --check > ansible-dryrun.log 2>&1"
                        archiveArtifacts artifacts: 'ansible-dryrun.log', allowEmptyArchive: true
                    }
                }

                stage('Puppet Dry-Run') {
                    agent { docker { image 'ubuntu:24.04' } }
                    steps {
                        unstash 'source'
                        sh 'apt-get update && apt-get install -y puppet-agent'
                        sh "puppet apply ${PUPPET_MANIFEST} --noop > puppet-dryrun.log 2>&1"
                        archiveArtifacts artifacts: 'puppet-dryrun.log', allowEmptyArchive: true
                    }
                }

                stage('SaltDry-Run') {
                    agent { docker { image 'ubuntu:24.04' } }
                    steps {
                        unstash 'source'
                        sh 'apt-get update && apt-get install -y salt-minion'
                        sh "salt-call --local state.apply ${SALT_STATE} test=True > salt-dryrun.log 2>&1"
                        archiveArtifacts artifacts: 'salt-dryrun.log', allowEmptyArchive: true
                    }
                }
            }
        }

        // ----------------------------------------------------------------- //
        // 11. Config-management – full deploy (parallel)
        // ----------------------------------------------------------------- //
        stage('Config-Mgmt Deploy') {
            when { branch 'main' }
            parallel {

                stage('Ansible Deploy') {
                    agent { docker { image 'python:3.14-slim' } }
                    steps {
                        unstash 'source'
                        sh 'pip install --no-cache-dir ansible'
                        sh "ansible-playbook -i ${ANSIBLE_INVENTORY} ansible/playbook.yml"
                    }
                }

                stage('Puppet Deploy') {
                    agent { docker { image 'ubuntu:24.04' } }
                    steps {
                        unstash 'source'
                        sh 'apt-get update && apt-get install -y puppet-agent'
                        sh "puppet apply ${PUPPET_MANIFEST}"
                    }
                }

                stage('Salt Deploy') {
                    agent { docker { image 'ubuntu:24.04' } }
                    steps {
                        unstash 'source'
                        sh 'apt-get update && apt-get install -y salt-minion'
                        sh "salt-call --local state.apply ${SALT_STATE}"
                    }
                }
            }
        }

        // ----------------------------------------------------------------- //
        // 12. Docker build & push (multi-arch, cache, Sigstore)
        // ----------------------------------------------------------------- //
        stage('Docker Build & Push') {
            agent { docker { image 'docker:25-dind' } }
           environment{
                DOCKER_BUILDKIT = '1'
            }
            steps {
                unstash 'source'
                withCredentials([usernamePassword(credentialsId: 'docker-credentials',
                                                usernameVariable: 'DOCKER_USER',
                                                passwordVariable: 'DOCKER_PASS')]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'

                    script {
                        def images = [
                            api    : [path: '.',               tag: 'api'],
                            ticket : [path: 'services/ticket-adapter-java', tag: 'ticket'],
                            admin  : [path: 'services/admin-portal',       tag:'admin'],
                            auditor: [path: 'services/auditor',            tag: 'auditor']
                        ]

                        images.each { name, cfg ->
                            def img = "${REGISTRY_URL}/astradesk-${cfg.tag}:${IMAGE_TAG}"
                            sh """
                                docker buildx create --use
                                docker buildx build \
                                  --platform linux/amd64,linux/arm64 \
                                  --cache-from type=registry,ref=${img} \
                                  --cache-to type=inline \
                                  -t ${img} \
                                  --push \
                                  ${cfg.path}
                            """
                            // Sigstore signing (requires COSIGN_PRIVATE_KEY in Jenkins)
                            withCredentials([file(credentialsId: 'cosign-key', variable: 'COSIGN_KEY')]) {
                                sh "cosign sign --key ${COSIGN_KEY} ${img}"
                            }
                        }
                    }
                }
            }
        }

        // ----------------------------------------------------------------- //
        //13. Apply Istio manifests + verify STRICT mTLS
        // ----------------------------------------------------------------- //
        stage('Istio Config') {
            agent { docker { image 'bitnami/kubectl:latest' } }
            steps {
                unstash 'source'
                withCredentials([file(credentialsId: env.KUBE_CREDENTIALS_ID, variable: 'KUBECONFIG')]) {
                    retry(3) {
                        sh 'kubectl apply -f deploy/istio/ --kubeconfig=$KUBECONFIG'
                        sh 'istioctl analyze -n ${HELM_NAMESPACE} --kubeconfig=$KUBECONFIG'
                    }
                    //Verify PeerAuthentication = STRICT
                    sh '''
                        kubectl get peerauthentication -n ${HELM_NAMESPACE} -o jsonpath='{.items[*].spec.mtls.mode}' \
                          | grep -q STRICT || (echo "mTLS not STRICT!" && exit 1)
                    '''
                }
            }
        }

        // ----------------------------------------------------------------- //
        // 14. Sync cert-manager TLS secret → Admin API
        // ----------------------------------------------------------------- //
        stage('Sync TLS Secret') {
            agent { docker { image 'bitnami/kubectl:latest' } }
            steps {
                unstash 'source'
                withCredentials([
                    file(credentialsId: env.KUBE_CREDENTIALS_ID, variable: 'KUBECONFIG'),
                    string(credentialsId: env.ADMIN_API_JWT_ID, variable: 'JWT')
                ]) {
                    sh '''
                        TLS_CERT=$(kubectl get secret -n ${HELM_NAMESPACE} astradesk-tls \
                                   -o jsonpath='{.data.tls\\.crt}' --kubeconfig=$KUBECONFIG | base64 -d)
                        curl -sSf -X POST "${ADMIN_API_URL}/secrets" \
                          -H "Authorization: Bearer $JWT" \
                          -H "Content-Type: application/json" \
                          -d '{
                            "name": "astradesk_mtls_cert",
                            "type": "certificate",
                            "value": "'"${TLS_CERT}"'"
                          }'
                    '''
                }
            }
        }

        // ----------------------------------------------------------------- //
        // 15. Helm lint → test → upgrade
        // ----------------------------------------------------------------- //
        stage('Helm Deploy') {
                    when { branch 'main' }
                    agent { docker { image 'alpine/helm:3.19.0' } }
                    steps {
                        unstash 'source'
                        withCredentials([file(credentialsId: env.KUBE_CREDENTIALS_ID, variable: 'KUBECONFIG')]) {
                            //Lint
                            sh 'helm lint deploy/chart'

                            // Dry-run test
                            sh '''
                                helm upgrade --dry-run astradesk deploy/chart \
                                --namespace ${HELM_NAMESPACE} \
                                --kubeconfig=$KUBECONFIG
                            '''

                            // Real upgrade (pull DB endpoints from Terraform output)
                            sh '''
                                POSTGRES_ENDPOINT=$(terraform -chdir=${TERRAFORM_DIR} output -raw rds_postgres_endpoint)
                                MYSQL_ENDPOINT=$(terraform -chdir=${TERRAFORM_DIR} output -raw rds_mysql_endpoint)

                                helm upgrade --install astradesk deploy/chart \
                                --setapi.image.repository=${REGISTRY_URL}/astradesk-api \
                                --set api.image.tag=${IMAGE_TAG} \
                                --set ticketAdapter.image.repository=${REGISTRY_URL}/astradesk-ticket \
                                --set ticketAdapter.image.tag=${IMAGE_TAG} \
                                --set admin.image.repository=${REGISTRY_URL}/astradesk-admin \
                                --set admin.image.tag=${IMAGE_TAG} \
                                --set auditor.image.repository=${REGISTRY_URL}/astradesk-auditor \
                                --set auditor.image.tag=${IMAGE_TAG} \
                                --set api.autoscaling.enabled=true \
                                --set api.autoscaling.minReplicas=2 \
                                --set api.autoscaling.maxReplicas=10 \
                                --set api.autoscaling.targetCPUUtilizationPercentage=60 \
                                --set ticketAdapter.autoscaling.enabled=true \
                                --set ticketAdapter.autoscaling.minReplicas=2 \
                                --set ticketAdapter.autoscaling.maxReplicas=5 \
                                --set ticketAdapter.autoscaling.targetCPUUtilizationPercentage=60 \
                                --set admin.autoscaling.enabled=true \
                                --set admin.autoscaling.minReplicas=2 \
                                --set admin.autoscaling.maxReplicas=5 \
                                --set admin.autoscaling.targetCPUUtilizationPercentage=60 \
                                --set auditor.autoscaling.enabled=true \
                                --set auditor.autoscaling.minReplicas=2 \
                                --set auditor.autoscaling.maxReplicas=5 \
                                --set auditor.autoscaling.targetCPUUtilizationPercentage=60 \
                                --set database.postgres.host=${POSTGRES_ENDPOINT} \
                                --set database.mysql.host=${MYSQL_ENDPOINT} \
                                --namespace ${HELM_NAMESPACE} \
                                --create-namespace \
                                --wait --timeout 6m \
                                --kubeconfig=$KUBECONFIG
                            '''
                        }
                    }
                }

            } 
        //end stages

    //  --------------------------------------------------------------------- //
    // Post actions
    // --------------------------------------------------------------------- //
    post {
        always {
            // Archive everything useful
            archiveArtifacts artifacts: '''
                coverage.xml,
                pytest-report.xml,
                **/jacocoTestReport.xml,
                services/admin-portal/coverage/**,
                infra/plan.out,
                *.log,
                aws-secret-response.json
            ''', allowEmptyArchive: true

            // JUnit reports
            junit testResults: '**/TEST-*.xml,pytest-report.xml', allowEmptyResults: true

            // Slack notification
            slackSend channel: env.SLACK_CHANNEL,
                      color: currentBuild.currentResult == 'SUCCESS' ? 'good' : 'danger',
                      message: "*${env.JOB_NAME}* #${env.BUILD_NUMBER} – ${currentBuild.currentResult}\n${env.BUILD_URL}"
        }

        cleanup {
            // Clean workspace on agents
            cleanWs()
        }
    }
}
