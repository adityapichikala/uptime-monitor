<div align="center">

# 📊 AI API Observatory: Industrial-Grade Architecture & Implementation Report

**Document Status:** Final / Production  
**Project:** AI API Observatory  
**Author:** Aditya Pichikala  
**Course:** INT377 — Cloud Computing & Automation  

---

*"A comprehensive, highly-available, and automated infrastructure for the real-time observability, validation, and telemetry of Large Language Model (LLM) APIs."*

</div>

<br><br>

---

## 1. Executive Summary

As the modern software landscape rapidly transitions toward AI-integrated capabilities, applications are becoming increasingly dependent on third-party Large Language Model (LLM) Application Programming Interfaces (APIs). Providers like OpenAI, Google Gemini, Anthropic, and HuggingFace act as critical external dependencies. Consequently, understanding the operational health, response latency, token consumption rates, financial cost trajectories, and semantic accuracy of these endpoints is no longer optional—it is a mission-critical requirement.

The **AI API Observatory** was engineered from the ground up to address this operational blind spot. It is an industrial-grade, highly resilient Cloud DevOps and System Administration platform. Rather than merely polling an API to check if it is "alive," this observatory evaluates the quality of the response, categorizes the specific nature of failures (e.g., distinguishing between a network timeout and a rate limit), and feeds this telemetry into a robust, real-time visualization dashboard.

This project implements a fully automated, scalable, and secure deployment pipeline utilizing a modern, best-in-class technology stack: **Python (FastAPI)**, **Docker**, **Terraform**, **Jenkins**, **Prometheus**, and **Grafana**. It serves as an authoritative blueprint for implementing resilient, observable, and automated cloud-native applications in an enterprise environment.

---

## 2. Architectural Deep Dive: The Dual-Server Paradigm

A fundamental design decision in this architecture is the strict segregation of concerns across **two separate AWS EC2 instances**. In amateur or hobbyist setups, it is common to deploy the application, the continuous integration/continuous deployment (CI/CD) engine, and the observability stack on a single server to minimize compute costs. For an industrial-grade environment, this constitutes a severe architectural anti-pattern.

### 2.1. The Problem with Single-Node Architectures

Deploying all services onto a single `t3.micro` instance introduces critical failure vectors:

| Failure Vector | Description | Business Impact |
| :--- | :--- | :--- |
| **Resource Contention (Noisy Neighbor)** | Jenkins is notoriously CPU and Memory intensive, especially during the Docker build phase and vulnerability scanning (`trivy`). If Jenkins spikes the CPU to 100%, the FastAPI application will experience severe latency or crash due to Out-Of-Memory (OOM) exceptions. | Application downtime triggered by internal deployment processes. |
| **Lack of Fault Isolation** | If the application code contains a memory leak or a runaway process that crashes the server, the Prometheus and Grafana instances residing on that same server will also go offline. | Complete loss of observability. The operations team is blinded exactly when they need metrics the most. |
| **Compromised Security Posture** | The CI/CD server contains highly privileged secrets (Docker Hub credentials, AWS IAM keys, deployment SSH keys). Placing it on the same network interface and instance as the public-facing application dramatically increases the attack surface. | A vulnerability in the public application could lead to a complete compromise of the deployment infrastructure. |

### 2.2. The Distributed Solution

By separating the architecture into **EC2-A (App Server)** and **EC2-B (Ops Server)**, we achieve enterprise-grade isolation.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AWS Cloud (us-east-1)                                 │
│                                                                                         │
│  ┌───────────────────────────────── VPC (10.0.0.0/16) ───────────────────────────────┐  │
│  │                                                                                   │  │
│  │  ┌──────────────────────── Public Subnet (10.0.1.0/24) ────────────────────────┐  │  │
│  │  │                                                                             │  │  │
│  │  │  ┌────────────────────────────────┐       ┌────────────────────────────────┐│  │  │
│  │  │  │       EC2-A: APP SERVER        │       │       EC2-B: OPS SERVER        ││  │  │
│  │  │  │       Instance: t3.micro       │       │       Instance: t3.micro       ││  │  │
│  │  │  │       Role: Production Traffic │       │       Role: Mgmt & Telemetry   ││  │  │
│  │  │  │                                │       │                                ││  │  │
│  │  │  │  ┌──────────────────────────┐  │       │  ┌──────────────────────────┐  ││  │  │
│  │  │  │  │      Docker Engine       │  │       │  │      Docker Engine       │  ││  │  │
│  │  │  │  │                          │  │       │  │                          │  ││  │  │
│  │  │  │  │  [ Container: fastapi ]  │◄─┼───────┼──┤  [ Container: jenkins ]  │  ││  │  │
│  │  │  │  │    Port: 30080 -> 8000   │  │ Deploy│  │    Port: 8080            │  ││  │  │
│  │  │  │  │                          │  │       │  │                          │  ││  │  │
│  │  │  │  └──────────────────────────┘  │       │  │  [ Container: prometheus]│  ││  │  │
│  │  │  │                ▲               │       │  │    Port: 9090            │  ││  │  │
│  │  │  └────────────────┼───────────────┘       │  │                          │  ││  │  │
│  │  │                   │ Scrape (/metrics)     │  │  [ Container: grafana ]  │  ││  │  │
│  │  │                   └───────────────────────┼──┤    Port: 3000            │  ││  │  │
│  │  │                                           │  └──────────────────────────┘  ││  │  │
│  │  │                                           └────────────────────────────────┘│  │  │
│  │  └─────────────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

#### EC2-A: App Server
Dedicated entirely to running the production FastAPI Docker container. Because it handles no build processes, the `t3.micro` instance can dedicate 100% of its compute to maintaining high-performance async loops for evaluating external AI APIs.

#### EC2-B: Ops Server
The nerve center of the infrastructure. It runs `docker-compose` to orchestrate three isolated containers: Jenkins, Prometheus, and Grafana. Even if the App Server fails completely, the Ops Server remains online, allowing Prometheus to trigger alerts and the operations team to deploy a fix via Jenkins.

---

## 3. Comprehensive Technology Stack & Service Breakdown

Every tool selected for this project represents an industry-standard best practice. Below is a detailed analysis of each service, its explicit role in this architecture, and the alternatives considered.

### 3.1. Infrastructure as Code (IaC): Terraform
*   **Role:** Automated Infrastructure Provisioning.
*   **Version Used:** `~> 5.0` (AWS Provider), `>= 1.5.0` (Terraform Core).
*   **Implementation Details:** Terraform completely replaces manual AWS console interactions. It builds the foundational network (VPC, Subnet, Internet Gateway, Route Tables). It provisions the EC2 instances, leveraging `aws_ssm_parameter` to dynamically fetch the latest secure Ubuntu 22.04 AMI. Crucially, it manages **Security Groups** and **IAM Roles**, ensuring that EC2-A can write logs to CloudWatch and EC2-B can dynamically read EC2 tags and write backups to S3.
*   **Why Not Alternatives?** While AWS CloudFormation is native to AWS, Terraform is cloud-agnostic and features a vastly superior and more readable configuration language (HCL). Pulumi was considered but requires a heavier programming overhead for infrastructure definitions.

### 3.2. Core Logic Engine: Python 3.11 & FastAPI
*   **Role:** High-Concurrency Async API and Background Worker.
*   **Version Used:** `Python 3.11.15`, `FastAPI 0.136.1`, `Uvicorn 0.47.0`.
*   **Implementation Details:** The core application checks multiple AI APIs. Doing this synchronously (checking one after another) would be catastrophically slow. FastAPI utilizes standard Python `asyncio`, allowing the application to fire off requests to Google Gemini, HuggingFace, and OpenRouter simultaneously. It also exposes a robust REST API for managing which providers are monitored at runtime without requiring a container restart.
*   **Why Not Alternatives?** Flask and Django are fundamentally synchronous frameworks and require heavy workarounds (like Celery/Redis) to handle background polling efficiently. Node.js (Express) handles async well, but Python possesses a vastly superior ecosystem for interacting with AI models (e.g., native SDKs for OpenAI, Gemini).

### 3.3. Containerization: Docker Engine
*   **Role:** Immutable Application Packaging.
*   **Version Used:** `Docker 29.1.3`.
*   **Implementation Details:** The FastAPI application is bundled into a lightweight `python:3.11-slim` container. This ensures that the application has the exact same operating system, dependencies, and environment variables whether it runs on a developer's laptop, inside Jenkins, or on the production EC2 instance.
*   **Why Not Alternatives?** Podman is an excellent daemonless alternative, but Docker remains the undisputed industry standard for CI/CD integrations and developer familiarity.

### 3.4. Orchestration & Telemetry: Prometheus & Grafana
*   **Role:** Time-Series Database and Observability UI.
*   **Version Used:** `Prometheus 3.11.3`, `Grafana 13.0.1+security-01`.
*   **Implementation Details:** 
    *   **Prometheus** is configured to execute a "pull" strategy. Every 15 seconds, it reaches out to the FastAPI container's `/metrics` endpoint. To prevent brittle hardcoding of IP addresses, Prometheus uses `ec2_sd_configs` (AWS Service Discovery) to automatically query the AWS API, find instances tagged as `ai-observatory-app`, and scrape them dynamically.
    *   **Grafana** connects to Prometheus and renders complex PromQL queries into beautiful, human-readable dashboards, displaying metrics like `api_response_time_seconds` and `api_tokens_used`.
*   **Why Not Alternatives?** Datadog or New Relic are powerful enterprise alternatives, but they are expensive SaaS products. The Prometheus/Grafana stack provides unparalleled, cost-free, open-source telemetry.

### 3.5. Continuous Integration/Deployment: Jenkins
*   **Role:** Automation and Delivery Pipeline.
*   **Version Used:** `Jenkins 2.555.2 LTS`.
*   **Implementation Details:** Jenkins automates the transition of code from a developer's machine to the live production server. The pipeline is codified in a `Jenkinsfile`, ensuring the build process itself is version-controlled.
*   **Why Not Alternatives?** GitHub Actions and GitLab CI are excellent managed services. However, running a self-hosted Jenkins instance demonstrates a profound, foundational understanding of how CI/CD engines actually operate under the hood, including credential management, agent execution, and secure shell (SSH) deployments.

---

## 4. Engineering Resiliency: Building for Failure

An industrial-grade application assumes that failure is inevitable. The network will drop packets, external APIs will rate-limit requests, and endpoints will suffer outages. The AI API Observatory implements advanced resilience strategies directly in the application code (`app/main.py`).

### 4.1. Strict Client Timeouts (Fail-Fast Mechanism)

**The Problem:** Free-tier or overloaded AI endpoints (like HuggingFace serverless inference) will occasionally accept a connection but hang indefinitely while attempting to generate a response. In an asynchronous Python loop, a hanging connection ties up resources and prevents the loop from iterating, causing the entire monitoring application to stall.

**The Solution:** The codebase enforces strict hardware-level timeouts on all client connections.
```python
client = AsyncOpenAI(api_key=api_key, base_url=provider.get("base_url"), timeout=15.0)
```
If the external AI provider fails to return a complete payload within exactly 15.0 seconds, the client deliberately severs the connection, logs a timeout error, and immediately proceeds to monitor the next provider.

### 4.2. Transient Error Handling (Tenacity Retry Decorators)

**The Problem:** A single dropped packet, a momentary DNS resolution failure, or a brief HTTP 429 (Too Many Requests) response shouldn't immediately trigger a "Critical System Down" alert.

**The Solution:** The application utilizes the robust `tenacity` library to decouple transient glitches from true outages. 
```python
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
async def check_groq_openai(...)
```
Every API call is wrapped in this decorator. If a request fails, the application silently waits 2 seconds and attempts the call again, up to a maximum of 3 times. Only if all three sequential attempts fail does the system record an error and mark the provider's status as `DOWN`.

### 4.3. Dynamic Metric Error Classification

**The Problem:** When building Grafana dashboards, a generic "error occurred" metric is not actionable. Operations teams need to know exactly *why* the provider failed.

**The Solution:** Instead of incrementing a generic `api_error_total` counter, the application dynamically parses the raw exception trace, categorizes the root cause, and attaches it as a label (`error_type`) to the Prometheus metric.

```python
        # Determine error type dynamically
        error_type = "generic_internal"
        exc_str = str(exc).lower()
        if "timeout" in exc_str or "timed out" in exc_str:
            error_type = "timeout"
        elif "rate limit" in exc_str or "429" in exc_str or "quota" in exc_str:
            error_type = "rate_limit_429"
        elif "401" in exc_str or "unauthorized" in exc_str or "credentials" in exc_str:
            error_type = "auth_401"
        elif "404" in exc_str or "not found" in exc_str:
            error_type = "not_found_404"

        api_error_total.labels(provider=name, error_type=error_type).inc()
```
**Impact:** Grafana can now render a pie chart displaying "Failure Root Causes," allowing engineers to instantly distinguish between a billing issue (HTTP 402) and an endpoint retirement (HTTP 404).

---

## 5. Security & DevSecOps Posture

Security is not an afterthought; it is integrated deeply into both the infrastructure and the CI/CD pipeline.

### 5.1. Continuous Vulnerability Scanning
The Jenkins pipeline implements a dedicated **Security Scan** stage before compiling any code:
1.  **Software Composition Analysis (SCA):** The `safety` Python module scans the `requirements.txt` file against a database of known vulnerabilities (CVEs) to ensure no malicious or deprecated libraries are introduced.
2.  **Container Scanning:** The `trivy` security scanner rigorously inspects the base `python:3.11-slim` Docker image. If any `HIGH` or `CRITICAL` OS-level vulnerabilities are detected, the pipeline automatically aborts the build, preventing vulnerable code from reaching production.

### 5.2. IAM Principle of Least Privilege
Terraform provisions highly restrictive AWS Identity and Access Management (IAM) Roles for the servers:
*   **App Server Role:** Only possesses permissions to write logs to CloudWatch. It cannot read S3 buckets or describe other instances.
*   **Ops Server Role:** Only possesses permissions to execute `ec2:DescribeInstances` (necessary for Prometheus Service Discovery) and `s3:PutObject` strictly to a designated `uptime-backup-*` bucket.

### 5.3. Secret Management
Zero credentials are hardcoded into the repository. 
*   **Local Development:** Secrets are kept in an `.env` file, which is strictly listed in `.gitignore`.
*   **Production:** Jenkins securely retrieves secrets from its encrypted Credentials Store and injects them dynamically into the Docker container as environment variables via the `docker run -e` flags at deployment time.

---

## 6. The 6-Stage CI/CD Pipeline Lifecycle

The `Jenkinsfile` orchestrates a seamless, automated journey from Git commit to live production deployment.

| Stage | Execution Details | Primary Purpose |
| :--- | :--- | :--- |
| **1. Checkout** | Executes `git clone` to pull the latest source code from the main branch. | Establishes the workspace baseline. |
| **2. Test** | Provisions an isolated Python virtual environment (`.venv`), installs dependencies, and executes the `pytest` suite located in `tests/test_api.py`. | Guarantees logical correctness before building. |
| **3. Security Scan** | Executes `safety check` on Python dependencies and `trivy image` on the Docker base OS. | Prevents vulnerable code from advancing to production. |
| **4. Build** | Executes `docker build -t`. The image is tagged dynamically using the Jenkins `$BUILD_NUMBER` to ensure strict version immutability. | Packages the application into an immutable artifact. |
| **5. Push** | Authenticates against Docker Hub using injected credentials and executes `docker push`. | Distributes the artifact to the global container registry. |
| **6. Deploy** | Establishes an SSH connection to the App Server. Stops the old container, pulls the new image, and executes a `docker run` command with injected API keys. Executes an AWS CLI script to back up state to S3. | Deploys the application with zero manual intervention. |

---

## 7. Deep-Dive Directory Hierarchy & File Map

Understanding the repository structure is critical for maintainability. This project strictly adheres to separation of concerns.

```text
uptime-monitor/
│
├── app/                              # ── CORE APPLICATION LAYER ──
│   ├── main.py                       # The heart of the system. Contains the FastAPI routes, 
│   │                                 # Prometheus metric definitions, background async polling 
│   │                                 # loop, and all tenacity retry logic.
│   ├── providers.json                # A dynamic dictionary of AI endpoints. Defines the models,
│   │                                 # base URLs, and token costs for OpenRouter, Gemini, and HF.
│   ├── prompts.json                  # A dictionary of semantic tests. Contains the input prompts
│   │                                 # and the strictly expected string answers to validate AI logic.
│   ├── requirements.txt              # Production dependency list (pinned versions of fastapi, 
│   │                                 # uvicorn, tenacity, httpx, prometheus-client, etc.).
│   └── .env.example                  # Safe template demonstrating required environment variables.
│
├── terraform/                        # ── INFRASTRUCTURE AS CODE LAYER ──
│   ├── main.tf                       # The master IaC file. Provisions the VPC, Subnet, Internet 
│   │                                 # Gateway, Route Tables, and uses user_data bash scripts 
│   │                                 # to bootstrap Docker and K3s onto the EC2 instances.
│   ├── iam.tf                        # Defines AWS Identity & Access Management Roles, Attachments,
│   │                                 # and Policies enforcing the Principle of Least Privilege.
│   ├── security_groups.tf            # The network firewall. Explicitly defines ingress/egress 
│   │                                 # TCP rules (e.g., locking down port 22, opening 8080/30080).
│   ├── outputs.tf                    # A utility script that prints the public IPs and constructed 
│   │                                 # URLs to the terminal upon successful infrastructure creation.
│   └── .terraform.lock.hcl           # Automatically generated hash file freezing provider versions.
│
├── grafana/                          # ── DASHBOARD PROVISIONING LAYER ──
│   ├── datasource.yml                # Configuration file auto-linking Grafana to the Prometheus DB.
│   ├── dashboard_provider.yml        # Directs the Grafana engine to auto-load JSON dashboard models.
│   └── observatory.json              # The massive, exported JSON payload containing the layout, 
│   │                                 # PromQL queries, and styling for the observability graphs.
│
├── cloudformation/                   # ── AWS BACKUP LAYER ──
│   └── backup-bucket.yaml            # An auxiliary IaC script to provision an AES-256 encrypted, 
│   │                                 # version-controlled S3 bucket for disaster recovery backups.
│
├── tests/                            # ── QUALITY ASSURANCE LAYER ──
│   └── test_api.py                   # The unit testing suite executed during the Jenkins pipeline.
│
├── Dockerfile                        # The blueprint for constructing the Python application container.
├── docker-compose.yml                # The orchestrator for the Ops Server. Boots Jenkins, Prometheus,
│                                     # and Grafana, linking them securely onto a shared bridge network.
├── prometheus.yml                    # The configuration dictating scrape intervals and establishing 
│                                     # the AWS EC2 dynamic Service Discovery rules.
├── Jenkinsfile                       # The Groovy script defining the 6-stage CI/CD pipeline.
├── test_setup.py                     # A local Python script used to automatically seed test data 
│                                     # (providers and prompts) into the running API via HTTP POST.
└── .gitignore                        # Prevents committing secrets, private keys, and terraform state.
```

---

## 8. Complete Master Installation & Setup Guide

This section provides the exhaustive, step-by-step commands required to completely reconstruct the AI API Observatory environment from a completely blank state.

### Phase 1: Local Environment Preparation & Verification
Before deploying to the cloud, the application must be verified locally.

1.  **Clone and Enter Repository:**
    ```bash
    git clone https://github.com/adityapichikala/uptime-monitor.git
    cd uptime-monitor/app
    ```
2.  **Environment Variable Hydration:**
    ```bash
    cp .env.example .env
    # Open .env using nano or VSCode and insert your active API keys
    ```
3.  **Virtual Environment Initialization & Dependency Rationale:**
    To ensure isolated execution, we utilize Python's native virtual environments.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
    *Why these specific requirements?* Every package in `requirements.txt` was selected for a critical architectural reason:

    | Package | Version | Architectural Purpose (Why We Use It) |
    | :--- | :--- | :--- |
    | `fastapi` | `0.111.0+` | **Core Web Framework:** Chosen for its native `async` support, enabling concurrent polling of multiple LLM APIs without blocking the main event thread. |
    | `uvicorn` | `0.29.0+` | **ASGI Server:** The high-performance web server that actually executes the FastAPI application. |
    | `httpx` | `0.27.0+` | **Async HTTP Client:** Replaces the standard `requests` library. Required to make non-blocking outbound network calls to external AI providers (like HuggingFace). |
    | `tenacity` | `8.2.0+` | **Resilience/Retry Engine:** Automatically intercepts network failures and HTTP 429 Rate Limits, executing exponential backoff retries to prevent false alarms. |
    | `prometheus-client` | `0.20.0+` | **Telemetry Exporter:** Exposes the `/metrics` endpoint in the exact text format required by the Prometheus scraping engine. |
    | `pydantic` | `2.7.0+` | **Data Validation:** Enforces strict typing for the JSON payloads submitted to the REST API (e.g., when adding a new provider). |
    | `openai` | `1.30.0+` | **Standardized API Client:** Used as a universal adapter to query OpenAI, OpenRouter, and Groq via their standardized endpoints. |
    | `google-generativeai` | `0.7.0+` | **Gemini SDK:** The official client required to communicate with Google's proprietary Gemini API. |
    | `slowapi` | `0.1.9+` | **Security (Rate Limiting):** Protects the FastAPI endpoints from DDoS attacks by strictly limiting requests per IP address. |

4.  **Boot the Application Engine:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
5.  **Smoke Test Execution:**
    In a secondary terminal window, execute the setup script to populate the database:
    ```bash
    cd uptime-monitor
    python test_setup.py
    ```
    *Validation:* Navigate to `http://localhost:8000/docs` to view the interactive API documentation and verify that `GET /providers` returns a populated JSON list.

### Phase 2: AWS Infrastructure Provisioning (Terraform)
This phase transforms AWS infrastructure into code, establishing the VPC and EC2 instances.

1.  **AWS CLI Authentication:** Ensure `aws configure` has been executed with an IAM user holding sufficient administrator privileges.
2.  **Terraform Execution:**
    ```bash
    cd uptime-monitor/terraform
    terraform init
    
    # Generate an execution plan for review
    terraform plan -var="key_name=YOUR_AWS_SSH_KEY_NAME" -var="your_ip=YOUR_PUBLIC_IP/32"
    
    # Apply the configuration to physically create the resources
    terraform apply -var="key_name=YOUR_AWS_SSH_KEY_NAME" -var="your_ip=YOUR_PUBLIC_IP/32" -auto-approve
    ```
3.  **Capture Output Artifacts:** Copy the generated `app_server_public_ip` and `ops_server_public_ip` strings to a secure notepad.

### Phase 3: Ops Server Initialization
The Ops Server handles the deployment and monitoring.

1.  **Secure Shell (SSH) Access:**
    ```bash
    ssh -i "your-key.pem" ubuntu@<OPS_SERVER_PUBLIC_IP>
    ```
2.  **Stack Verification:** The Terraform `user_data` script has already installed Docker and executed docker-compose.
    ```bash
    cd /home/ubuntu/uptime-monitor
    sudo docker-compose ps
    ```
    *Validation:* Ensure that the states for `jenkins`, `prometheus`, and `grafana` all read `Up`.

### Phase 4: Jenkins Pipeline Configuration
This configures the automation engine to push code to the App Server.

1.  **Access Jenkins:** Navigate a web browser to `http://<OPS_SERVER_PUBLIC_IP>:8080`.
2.  **Unlock the Instance:**
    ```bash
    sudo docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
    ```
    Paste this password into the UI, select "Install Suggested Plugins," and create an Admin User.
3.  **Credential Hydration:** Navigate to *Manage Jenkins -> Credentials -> System -> Global credentials*. You must strictly add the following ID names to match the `Jenkinsfile`:
    *   `dockerhub-creds` *(Type: Username with password)* - Your DockerHub credentials.
    *   `openrouter-api-key` *(Type: Secret text)*
    *   `gemini-api-key` *(Type: Secret text)*
    *   `hf-api-key` *(Type: Secret text)*
    *   `ec2-ssh-key-b64` *(Type: Secret text)* - You must base64 encode your `.pem` key file and paste the resulting string here.
4.  **Pipeline Creation:**
    *   Click "New Item" -> "Pipeline" -> Name it `ai-observatory`.
    *   Under the "Pipeline" section, select "Pipeline script from SCM".
    *   SCM: `Git`.
    *   Repository URL: `https://github.com/adityapichikala/uptime-monitor.git`
    *   Script Path: `Jenkinsfile`
    *   Save and click **Build Now**. Watch the console logs as Jenkins successfully deploys the code.

### Phase 5: Final Validation & Telemetry Review

1.  **Verify Application:** `http://<APP_SERVER_PUBLIC_IP>:30080/docs`
2.  **Verify Prometheus Discovery:** `http://<OPS_SERVER_PUBLIC_IP>:9090/targets`. You must see the `ai-observatory-dynamic` job displaying a green `UP` status.
3.  **Verify Grafana Dashboards:** `http://<OPS_SERVER_PUBLIC_IP>:3000`. Log in with `admin/admin`. Navigate to Dashboards, and you will see the beautifully rendered, real-time charts mapping the health of your AI APIs.

---

## 9. Operations & Maintenance (O&M) Handbook

An industrial-grade system requires runtime flexibility. The FastAPI application exposes robust endpoints to manipulate its state without requiring a destructive container restart.

### 9.1. Managing API Keys (Environment Variable Updates)
Because API keys are injected via Docker environment variables, updating a revoked or expired key requires a container recreation on the App Server.

```bash
# 1. SSH into the App Server
ssh -i "your-key.pem" ubuntu@<APP_SERVER_PUBLIC_IP>

# 2. Halt and destroy the old container instance
sudo docker stop fastapi-app
sudo docker rm fastapi-app

# 3. Spin up the new instance with updated -e flags
sudo docker run -d --name fastapi-app \
  -p 30080:8000 \
  -e OPENROUTER_API_KEY='sk-or-v1-NEW_KEY_HERE' \
  -e GEMINI_API_KEY='NEW_KEY_HERE' \
  -e HF_API_KEY='hf_NEW_KEY_HERE' \
  --restart always \
  adityapichikala/ai-observatory:latest
```

### 9.2. Injecting New Evaluation Prompts (Zero Downtime)
If you wish to test the AI's math skills instead of geographic knowledge, you can inject a new prompt live via curl.

```bash
curl -X POST http://<APP_SERVER_PUBLIC_IP>:30080/prompts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is the square root of 144? Answer with just the number.",
    "expected_answer": "12"
  }'
```
*Impact:* The background checking loop will automatically incorporate this new semantic test on its very next iteration.

### 9.3. Registering New AI Providers (Zero Downtime)
To expand the observatory to monitor a new endpoint (e.g., Anthropic via an OpenAI-compatible endpoint), simply POST the new provider details.

```bash
curl -X POST http://<APP_SERVER_PUBLIC_IP>:30080/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Anthropic-Claude",
    "api_key": "OPENROUTER_API_KEY",
    "model": "anthropic/claude-3-opus",
    "provider_type": "openrouter",
    "base_url": "https://openrouter.ai/api/v1",
    "cost_per_1k_tokens": 0.015
  }'
```

### 9.4. Modifying Polling Frequency (Zero Downtime)
To increase the frequency of checks from every 120 seconds to every 60 seconds:
```bash
curl -X PUT http://<APP_SERVER_PUBLIC_IP>:30080/config \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 60}'
```

---

## 10. Visual Documentation & UI Telemetry

To provide a complete understanding of the user interfaces utilized in the Ops Server stack, below is the visual documentation for the Continuous Integration and Telemetry dashboards.

*(Note: If deploying this project, replace the placeholder images below with actual screenshots of your running EC2 instances by placing them in an `assets/` folder in your repository).*

### 10.1. Jenkins (CI/CD Pipeline UI)
**Purpose:** Displays the real-time execution of the 6-stage deployment pipeline, including security scan outputs and Docker push statuses.
<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/e/e9/Jenkins_logo.svg" alt="Jenkins Dashboard" width="200"/>
  <p><i>Figure 1: Jenkins Automation Server Interface</i></p>
</div>

### 10.2. Prometheus (Targets & SD UI)
**Purpose:** Confirms that the AWS EC2 Service Discovery successfully located the App Server and is actively scraping the `/metrics` endpoint.
<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/3/38/Prometheus_software_logo.svg" alt="Prometheus Targets" width="200"/>
  <p><i>Figure 2: Prometheus Targets & Discovery Interface</i></p>
</div>

### 10.3. Grafana (Real-Time Observability Dashboard)
**Purpose:** The final aggregation point. Renders complex PromQL queries into actionable, real-time visual charts for latency, token consumption, and failure classifications.
<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/3/3b/Grafana_icon.svg" alt="Grafana Dashboard" width="200"/>
  <p><i>Figure 3: Grafana Real-Time Observability Dashboard</i></p>
</div>

---

<div align="center">

**End of Comprehensive Architecture & Implementation Report.**

</div>
