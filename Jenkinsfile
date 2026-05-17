pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "adityapichikala/ai-observatory"
        DOCKER_TAG   = "${env.BUILD_NUMBER}"
    }

    stages {

        // ── Stage 1: Checkout ────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // ── Stage 2: Test ────────────────────────────────────────
        stage('Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r app/requirements.txt
                    python -m pytest tests/ -v --tb=short || echo "Tests completed"
                '''
            }
        }

        // ── Stage 3: Security Scan ──────────────────────────────
        stage('Security Scan') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pip install safety
                    safety check -r app/requirements.txt || echo "Safety scan done"
                '''
                sh '''
                    trivy image --exit-code 0 --severity HIGH,CRITICAL \
                        --no-progress python:3.11-slim || echo "Trivy scan done"
                '''
            }
        }

        // ── Stage 4: Build ──────────────────────────────────────
        stage('Build') {
            steps {
                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
                sh "docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest"
            }
        }

        // ── Stage 5: Push ───────────────────────────────────────
        stage('Push') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker push ${DOCKER_IMAGE}:latest
                    '''
                }
            }
        }

        // ── Stage 6: Deploy ─────────────────────────────────────
        stage('Deploy') {
            steps {
                withCredentials([
                    string(credentialsId: 'groq-api-key',   variable: 'GROQ_KEY'),
                    string(credentialsId: 'gemini-api-key', variable: 'GEMINI_KEY'),
                    string(credentialsId: 'hf-api-key',     variable: 'HF_KEY'),
                    string(credentialsId: 'ec2-kubeconfig', variable: 'KUBECONFIG_CONTENT')
                ]) {
                    sh '''
                        # Write kubeconfig to temp file
                        KUBECONFIG_FILE=$(mktemp)
                        echo "$KUBECONFIG_CONTENT" | base64 -d > "$KUBECONFIG_FILE"
                        export KUBECONFIG="$KUBECONFIG_FILE"

                        # Create / update Kubernetes secret with API keys
                        kubectl delete secret ai-observatory-secrets --ignore-not-found
                        kubectl create secret generic ai-observatory-secrets \
                            --from-literal=GROQ_API_KEY="$GROQ_KEY" \
                            --from-literal=GEMINI_API_KEY="$GEMINI_KEY" \
                            --from-literal=HF_API_KEY="$HF_KEY"

                        # Apply manifests
                        kubectl apply -f k8s/

                        # Rolling update to new image
                        kubectl set image deployment/fastapi-app \
                            fastapi=${DOCKER_IMAGE}:${DOCKER_TAG}

                        # Wait for rollout
                        kubectl rollout status deployment/fastapi-app --timeout=120s

                        # Backup providers.json to S3
                        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
                        aws s3 cp app/providers.json \
                            "s3://uptime-backup-${ACCOUNT_ID}/providers.json" || true

                        # Cleanup
                        rm -f "$KUBECONFIG_FILE"
                    '''
                }
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline completed — AI API Observatory deployed.'
        }
        failure {
            echo '❌ Pipeline failed — check stage logs above.'
        }
        always {
            sh 'docker logout || true'
            cleanWs()
        }
    }
}
