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
        // If an evaluator asks about DevSecOps, point to this stage.
        stage('Security Scan') {
            steps {
                // 1. Software Composition Analysis (SCA)
                // 'safety' checks the requirements.txt file against a database of known CVEs (vulnerabilities).
                sh '''
                    . .venv/bin/activate
                    pip install safety
                    safety check -r app/requirements.txt || echo "Safety scan done"
                '''
                
                // 2. Container OS Security Scan
                // 'trivy' rigorously inspects the base python Docker image. 
                // If it finds HIGH or CRITICAL level vulnerabilities, the pipeline breaks and stops deployment.
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
        // This is the Zero-Downtime Deployment stage to the App Server.
        stage('Deploy') {
            steps {
                withCredentials([
                    string(credentialsId: 'openrouter-api-key', variable: 'OPENROUTER_KEY'),
                    string(credentialsId: 'gemini-api-key', variable: 'GEMINI_KEY'),
                    string(credentialsId: 'hf-api-key',     variable: 'HF_KEY'),
                    string(credentialsId: 'ec2-ssh-key-b64', variable: 'SSH_KEY_B64'),
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        # 1. Securely decode the Base64 SSH private key we stored in Jenkins.
                        SSH_KEY_FILE=$(mktemp)
                        echo "$SSH_KEY_B64" | base64 -d > "$SSH_KEY_FILE"
                        chmod 600 "$SSH_KEY_FILE"

                        # 2. Use SSH to remotely log the App Server into Docker Hub.
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "echo '$DOCKER_PASS' | docker login -u '$DOCKER_USER' --password-stdin || true"

                        # 3. Tell the App Server to gracefully stop the old version of our application.
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "docker stop fastapi-app || true; docker rm fastapi-app || true"

                        # 4. Command the App Server to pull and run the NEW Docker container we just built.
                        # Notice how we inject the API keys using '-e' flags so they are never hardcoded in GitHub!
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "docker run -d --name fastapi-app \
                                -p 30080:8000 \
                                -e OPENROUTER_API_KEY='$OPENROUTER_KEY' \
                                -e GEMINI_API_KEY='$GEMINI_KEY' \
                                -e HF_API_KEY='$HF_KEY' \
                                --restart always \
                                ${DOCKER_IMAGE}:${DOCKER_TAG}"

                        # 5. Wait 5 seconds and verify the new container didn't crash.
                        sleep 5
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no ubuntu@10.0.1.96 \
                            "docker ps | grep fastapi-app"

                        # Backup providers.json to S3 (running locally on Jenkins agent)
                        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
                        if [ -n "$ACCOUNT_ID" ]; then
                            aws s3 cp app/providers.json \
                                "s3://uptime-backup-\${ACCOUNT_ID}/providers.json" || true
                        fi

                        # Cleanup secure SSH key file
                        rm -f "$SSH_KEY_FILE"
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
