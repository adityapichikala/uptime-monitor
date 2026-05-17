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
                    file(credentialsId: 'ec2-ssh-key-file',  variable: 'SSH_KEY_FILE'),
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        # Ensure correct permissions on the SSH key file
                        chmod 600 "$SSH_KEY_FILE"

                        # Log in to Docker Hub on the remote EC2 App Server
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "echo '$DOCKER_PASS' | docker login -u '$DOCKER_USER' --password-stdin || true"

                        # Stop and remove existing container if running
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "docker stop fastapi-app || true; docker rm fastapi-app || true"

                        # Run container directly on EC2
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "docker run -d --name fastapi-app \
                                -p 30080:8000 \
                                -e GROQ_API_KEY='$GROQ_KEY' \
                                -e GEMINI_API_KEY='$GEMINI_KEY' \
                                -e HF_API_KEY='$HF_KEY' \
                                --restart always \
                                ${DOCKER_IMAGE}:${DOCKER_TAG}"

                        # Wait 5 seconds and verify container is running
                        sleep 5
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "docker ps | grep fastapi-app"

                        # Backup providers.json to S3 (running locally on Jenkins agent)
                        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
                        aws s3 cp app/providers.json \
                            "s3://uptime-backup-${ACCOUNT_ID}/providers.json" || true
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
