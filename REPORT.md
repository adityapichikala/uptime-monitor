# 🚀 AI API Observatory: Comprehensive Architecture & Implementation Report

**Document Status:** Final / Production
**Project:** AI API Observatory
**Author:** Aditya Pichikala
**Course:** INT377 — Cloud Computing & Automation

---

## 1. Executive Summary

The **AI API Observatory** is an industrial-grade, highly resilient Cloud DevOps and System Administration project. Its primary purpose is to continuously monitor, evaluate, and observe multiple Large Language Model (LLM) Application Programming Interfaces (APIs). In an era where applications increasingly depend on third-party AI services, understanding the health, latency, token consumption, financial cost, and semantic accuracy of these endpoints is mission-critical.

This project implements a fully automated, scalable, and secure deployment pipeline. It evaluates leading AI providers—such as **Google Gemini**, **HuggingFace**, and **OpenRouter**—in real-time. By leveraging a modern technology stack encompassing **Python (FastAPI)**, **Docker**, **Terraform**, **Jenkins**, **Prometheus**, and **Grafana**, the AI API Observatory serves as a blueprint for implementing resilient, observable, and automated cloud-native applications.

---

## 2. System Architecture & Design Rationale

### 2.1. The Dual-Server (Two EC2 Instance) Architecture

A core design decision in this project is the strict segregation of concerns by deploying the system across two separate AWS EC2 instances (`t3.micro`) within a custom Virtual Private Cloud (VPC). 

#### Why Use Two EC2 Servers Instead of One?

In a development or hobbyist environment, it is common to run the application, the CI/CD pipeline, and the monitoring stack on a single server to save costs. However, in an industrial-grade production environment, this is an anti-pattern for several critical reasons:

1. **Resource Contention (The "Noisy Neighbor" Problem):** 
   - **Jenkins** is highly resource-intensive, especially during the build stage when it compiles Docker images and runs security scans. If Jenkins runs on the same server as the live FastAPI application, a pipeline execution will consume CPU and memory, causing the live application's latency to spike or the application to crash due to OOM (Out of Memory) errors.
   - **Prometheus** continuously ingests time-series data. This disk I/O and memory usage must not impact the application's ability to serve user traffic.
2. **High Availability and Fault Isolation:**
   - If the application server crashes due to a memory leak or an underlying infrastructure issue, the monitoring server remains online. This allows Prometheus to record the downtime and Alertmanager to notify the operations team. If both shared a server, a server crash would result in a total blackout, blinding the operations team.
3. **Security Posture:**
   - The CI/CD server (Jenkins) holds highly privileged secrets, such as Docker Hub credentials, AWS API keys, and deployment SSH keys. Exposing the CI/CD server to the same network footprint or machine as the public-facing application increases the blast radius of a potential compromise.

### 2.2. Network Flow and Topology

```text
┌───────────────────────────────── AWS Cloud (us-east-1) ─────────────────────────────────┐
│                                                                                         │
│  ┌─────────────────────────── VPC (10.0.0.0/16) ───────────────────────────┐           │
│  │                                                                          │           │
│  │  ┌─────────────── Public Subnet (10.0.1.0/24) ───────────────┐           │           │
│  │  │                                                           │           │           │
│  │  │  ┌─────────────────────────┐     ┌────────────────────────┐  │           │           │
│  │  │  │   EC2-A: App Server     │     │   EC2-B: Ops Server    │  │           │           │
│  │  │  │   (t3.micro)            │     │   (t3.micro)           │  │           │           │
│  │  │  │                         │     │                        │  │           │           │
│  │  │  │  ┌───────────────────┐  │     │  ┌──────────────────┐  │  │           │           │
│  │  │  │  │  Docker Container │  │     │  │  Jenkins :8080   │  │  │           │           │
│  │  │  │  │  (fastapi-app)     │  │     │  │  (CI/CD)         │  │  │           │           │
│  │  │  │  │                   │◄─┼─────┼──┘                  │  │  │           │           │
│  │  │  │  │  FastAPI Port:    │  │     │  ┌──────────────────┐  │  │           │           │
│  │  │  │  │  30080 -> 8000    │◄─┼─────┼──┤ Prometheus :9090 │  │  │           │           │
│  │  │  │  └───────────────────┘  │     │  │ (scrapes /metrics)  │  │           │           │
│  │  │  └─────────────────────────┘     │  └──────────────────┘  │  │           │           │
│  │  │                                  │  ┌──────────────────┐  │  │           │           │
│  │  │                                  │  │ Grafana :3000    │  │  │           │           │
│  │  │                                  │  │ (dashboards)     │  │  │           │           │
│  │  │                                  │  └──────────────────┘  │  │           │           │
│  │  │                                  └────────────────────────┘  │           │           │
│  │  └───────────────────────────────────────────────────────────────┘           │           │
│  └──────────────────────────────────────────────────────────────────────────┘           │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

**Data Flow Sequence:**
1. Code is pushed to GitHub.
2. Jenkins (on EC2-B) detects the webhook, pulls the code, tests, scans, builds a Docker image, and pushes it to Docker Hub.
3. Jenkins executes a remote SSH command into EC2-A to pull the new image and restart the `fastapi-app` container.
4. The `fastapi-app` (EC2-A) performs its background monitoring of external AI APIs every 120 seconds.
5. Prometheus (EC2-B) dynamically discovers EC2-A via AWS API and scrapes the `/metrics` endpoint every 15 seconds.
6. Grafana (EC2-B) queries Prometheus to render real-time observability dashboards.

---

## 3. Comprehensive Service Breakdown

Every service in this project was selected for its specific industry-standard capabilities.

### 3.1. Infrastructure Provisioning: Terraform
**Role:** Infrastructure as Code (IaC)
**Usage:** Terraform automates the creation of the foundational AWS infrastructure. Instead of manually clicking through the AWS console, `main.tf` defines the VPC, subnets, Internet Gateway, route tables, and the two EC2 instances. `security_groups.tf` strictly defines firewall rules (e.g., exposing only ports 8080, 9090, 3000, 30080, and 22). `iam.tf` implements the Principle of Least Privilege, granting the Ops server access to read EC2 tags (for Prometheus discovery) and write to S3 (for backups), while granting the App server access to CloudWatch.
**Alternatives:** AWS CloudFormation, Pulumi, Ansible.

### 3.2. Core Application: Python & FastAPI
**Role:** Backend API & Background Worker
**Usage:** Python 3.11 is used alongside FastAPI. FastAPI was chosen because it is natively asynchronous, allowing the application to check multiple AI APIs concurrently without blocking the main event loop. The app manages a REST API for adding/removing providers and prompts dynamically, while a background `asyncio` task polls the AI APIs every 120 seconds.
**Alternatives:** Node.js (Express), Go (Gin), Java (Spring Boot).

### 3.3. Containerization: Docker
**Role:** Application Packaging and Isolation
**Usage:** The FastAPI application is containerized using a `Dockerfile` based on `python:3.11-slim`. This ensures the "it works on my machine" problem is eliminated; the application behaves identically on the developer's laptop, the Jenkins build environment, and the production EC2 server. On the Ops server, `docker-compose` is utilized to orchestrate Jenkins, Prometheus, and Grafana in a unified network stack.
**Alternatives:** Podman, LXC/LXD.

### 3.4. Continuous Integration & Deployment (CI/CD): Jenkins
**Role:** Automation Engine
**Usage:** Jenkins handles the entire lifecycle from code commit to deployment. The `Jenkinsfile` defines a declarative, 6-stage pipeline:
1. **Checkout:** Pulls from Git.
2. **Test:** Runs `pytest` to validate application logic.
3. **Security Scan:** Uses `safety` to check Python dependencies for CVEs, and `trivy` to scan the Docker base image for vulnerabilities.
4. **Build:** Compiles the Docker image.
5. **Push:** Authenticates and uploads the image to Docker Hub.
6. **Deploy:** Safely SSHes into the App server, executes a zero-downtime rolling restart of the Docker container, and backs up configuration state to AWS S3.
**Alternatives:** GitHub Actions, GitLab CI, CircleCI.

### 3.5. Metrics & Time-Series Database: Prometheus
**Role:** Data Collection
**Usage:** Prometheus is configured to poll (scrape) the FastAPI application's `/metrics` endpoint. It uses AWS EC2 Service Discovery (`ec2_sd_configs`), which means it automatically queries the AWS API to find instances tagged as `ai-observatory-app` and dynamically adds them to its scrape list. This means if the App Server's IP changes, Prometheus adapts instantly without manual reconfiguration.
**Alternatives:** InfluxDB, Datadog, AWS CloudWatch Metrics.

### 3.6. Visualization: Grafana
**Role:** Data Dashboarding
**Usage:** Grafana connects to Prometheus as its data source. It uses pre-provisioned dashboards defined via code (in the `grafana/` directory) to display the metrics visually. It plots uptime, token usage, financial cost, and dynamic error classifications in easy-to-read charts, providing immediate situational awareness.
**Alternatives:** Kibana (ELK Stack), Tableau, Superset.

---

## 4. Key Engineering & Resiliency Decisions

To elevate this project to industrial standards, several advanced software engineering practices were implemented:

1. **Strict Client Timeouts:** 
   When querying external AI APIs (like OpenRouter or HuggingFace), network packets can drop, causing the HTTP client to hang indefinitely. We implemented a strict **15.0-second timeout** on all external `httpx` and `AsyncOpenAI` clients. If the provider fails to respond in 15 seconds, the application fails fast, records a timeout metric, and continues operating without locking up the server.

2. **Transient Error Handling (Tenacity Retries):**
   A single dropped packet shouldn't trigger an SLA violation alert. We implemented the `tenacity` Python library. The application automatically intercepts network failures and HTTP 429 (Rate Limit) errors, transparently retrying the request up to **3 times** with a **2-second backoff delay** before officially declaring the provider as `DOWN`.

3. **Granular Metric Error Classification:**
   Instead of a generic `api_error_total` metric, the `try/except` blocks dynamically parse the exception string. The metric is updated with an `error_type` label mapping the root cause to specific categories: `timeout`, `rate_limit_429`, `auth_401`, `payment_required_402`, or `not_found_404`. This allows Grafana to generate pie charts showing exactly *why* providers are failing.

---

## 5. Detailed Project File Structure

Every file in this repository is strictly necessary.

```text
uptime-monitor/
├── app/                              # Application Logic
│   ├── main.py                       # Core FastAPI application, metrics definition, check loop
│   ├── providers.json                # Pre-populated list of AI endpoints to monitor
│   ├── prompts.json                  # Semantic tests to evaluate AI responses
│   ├── requirements.txt              # Pinned Python package dependencies
│   └── .env.example                  # Template for required environment variables
│
├── terraform/                        # Infrastructure as Code
│   ├── main.tf                       # Defines VPC, Subnet, EC2 instances, and boot scripts
│   ├── iam.tf                        # Defines AWS IAM Roles and Policies
│   ├── security_groups.tf            # Defines inbound/outbound networking rules
│   ├── outputs.tf                    # Outputs public IP addresses post-deployment
│   └── .terraform.lock.hcl           # Freezes Terraform provider versions
│
├── grafana/                          # Dashboard as Code
│   ├── datasource.yml                # Automatically links Grafana to Prometheus
│   ├── dashboard_provider.yml        # Directs Grafana to load JSON dashboards
│   └── observatory.json              # The exported JSON architecture of the charts
│
├── cloudformation/                   # Backup Infrastructure
│   └── backup-bucket.yaml            # Provisions an encrypted, versioned S3 bucket
│
├── tests/                            # Quality Assurance
│   └── test_api.py                   # Pytest suite executed during Jenkins CI
│
├── Dockerfile                        # Blueprint for the Python application container
├── docker-compose.yml                # Orchestrates Ops Server stack (Jenkins/Prometheus/Grafana)
├── prometheus.yml                    # Configures metrics scraping and AWS Service Discovery
├── Jenkinsfile                       # Defines the Groovy-based 6-stage CI/CD pipeline
├── test_setup.py                     # Python script to seed test data into the running API
└── .gitignore                        # Prevents committing secrets (.env) and local state (.tfstate)
```

---

## 6. Complete Setup & Installation Guide

This guide allows any engineer to replicate the AI API Observatory from scratch.

### Phase 1: Local Development & Smoke Test

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adityapichikala/uptime-monitor.git
   cd uptime-monitor/app
   ```
2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env and insert your API keys (OpenRouter, Gemini, HuggingFace)
   ```
3. **Initialize Virtual Environment & Run:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Test:** Navigate to `http://localhost:8000/docs` to view the Swagger UI.

### Phase 2: AWS Infrastructure Provisioning

1. **Authenticate with AWS:**
   Ensure `aws configure` is setup with your credentials.
2. **Execute Terraform:**
   ```bash
   cd ../terraform
   terraform init
   terraform plan -var="key_name=YOUR_AWS_SSH_KEY_NAME" -var="your_ip=YOUR_PUBLIC_IP/32"
   terraform apply -var="key_name=YOUR_AWS_SSH_KEY_NAME" -var="your_ip=YOUR_PUBLIC_IP/32"
   ```
3. **Note Outputs:** Save the `app_server_public_ip` and `ops_server_public_ip` printed to the console.

### Phase 3: Initializing the Ops Server

1. **Access the Ops Server:**
   ```bash
   ssh -i "your-key.pem" ubuntu@<OPS_SERVER_PUBLIC_IP>
   ```
2. **Verify Services:** The `user_data` script in Terraform automatically installed Docker and started the stack.
   ```bash
   cd /home/ubuntu/uptime-monitor
   docker-compose ps
   ```
   *(Ensure Jenkins, Prometheus, and Grafana are 'Up')*

### Phase 4: CI/CD Configuration (Jenkins)

1. **Access Jenkins UI:** Open `http://<OPS_SERVER_PUBLIC_IP>:8080`.
2. **Unlock Jenkins:** Retrieve the password:
   ```bash
   docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
3. **Configure Credentials:** Navigate to *Manage Jenkins -> Credentials* and add:
   - `dockerhub-creds` (Username/Password for DockerHub)
   - `openrouter-api-key` (Secret text)
   - `gemini-api-key` (Secret text)
   - `hf-api-key` (Secret text)
   - `ec2-ssh-key-b64` (Secret text: Base64 encoded contents of your `your-key.pem`)
4. **Create Pipeline:** Create a new Pipeline Job, point it to your GitHub repository, and specify `Jenkinsfile` as the script path.
5. **Run Build:** Click "Build Now". Jenkins will test, scan, build, and deploy the application to the App Server.

### Phase 5: Verification & Observability

1. **App Server API:** Visit `http://<APP_SERVER_PUBLIC_IP>:30080/docs` to ensure the API is running.
2. **Prometheus Targets:** Visit `http://<OPS_SERVER_PUBLIC_IP>:9090/targets`. Verify `ai-observatory-dynamic` is dynamically discovered and marked `UP`.
3. **Grafana Dashboards:** Visit `http://<OPS_SERVER_PUBLIC_IP>:3000` (Login: `admin` / `admin`). The AI API Observatory dashboard will be pre-loaded and displaying live data.

---

## 7. Operational Guide

### Adding a New API Key
Environment variables are injected during the Jenkins deployment. To update them manually on the App server:
```bash
sudo docker stop fastapi-app && sudo docker rm fastapi-app
sudo docker run -d --name fastapi-app -p 30080:8000 \
  -e OPENROUTER_API_KEY='NEW_KEY' \
  -e GEMINI_API_KEY='NEW_KEY' \
  --restart always adityapichikala/ai-observatory:latest
```

### Modifying Configuration at Runtime (Zero Downtime)
The application exposes REST endpoints to manipulate state without restarting the container:
- **Add a Test Prompt:** POST to `/prompts` via Swagger.
- **Add a New Provider:** POST to `/providers` via Swagger.
- **Change Polling Interval:** PUT to `/config` with payload `{"interval_seconds": 60}`.

---
**End of Report.**
