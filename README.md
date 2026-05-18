<div align="center">

# 🔭 AI API Observatory

### Real-Time AI Provider Health, Latency, Cost & Validity Monitoring

[![Python 3.11](https://img.shields.io/badge/Python-3.11.15-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI 0.136](https://img.shields.io/badge/FastAPI-0.136.1-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker 29.1](https://img.shields.io/badge/Docker-29.1.3-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Jenkins 2.555](https://img.shields.io/badge/Jenkins-2.555.2_LTS-D24939?logo=jenkins&logoColor=white)](https://jenkins.io)
[![Terraform ≥1.5](https://img.shields.io/badge/Terraform-≥1.5-7B42BC?logo=terraform&logoColor=white)](https://terraform.io)
[![Prometheus 3.11](https://img.shields.io/badge/Prometheus-3.11.3-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io)
[![Grafana 13.0](https://img.shields.io/badge/Grafana-13.0.1-F46800?logo=grafana&logoColor=white)](https://grafana.com)

</div>

---

## 📖 What Is This Project?

**AI API Observatory** is a production-grade DevOps monitoring system that continuously checks whether AI API providers are **online**, **fast**, **affordable**, and **accurate** — every 120 seconds, fully automated.

It monitors three live AI providers simultaneously:

| Provider | Model | Type | Free Tier |
|----------|-------|------|-----------|
| **OpenRouter** | `meta-llama/llama-3.3-70b-instruct:free` | Chat completion (OpenAI-compatible) | ✅ Yes |
| **Google Gemini** | `gemini-2.5-flash` | Native Gemini SDK | ✅ Yes (25 req/day) |
| **HuggingFace** | `facebook/bart-large-cnn` | Serverless Inference API | ✅ Yes |

> **Alternative providers you can use instead:** Groq (Llama 3), Anthropic Claude, Cohere, Mistral, Together AI, or any OpenAI-compatible endpoint. The app supports adding new providers at runtime via REST API — no code changes needed.

### What does it track?

| Metric | What It Measures | Prometheus Name |
|--------|-----------------|-----------------|
| **Uptime** | Is the API reachable? (1=up, 0=down) | `api_up` |
| **Latency** | Response time in seconds | `api_response_time_seconds` |
| **Token Usage** | Tokens consumed per call | `api_tokens_used` |
| **Cost** | Estimated USD cost per call | `api_cost_usd` |
| **Validity** | Did the model return the expected answer? | `api_response_valid` |
| **Errors** | Error count by type (timeout, 429, 401, etc.) | `api_error_total` |
| **Request Count** | Total requests sent | `api_requests_total` |

---

## 📐 Architecture: Why Two EC2 Servers?

We use **two separate EC2 instances** instead of one. Here is **why**:

### The Problem With a Single Server
If you run everything (your app + Jenkins + Prometheus + Grafana) on one machine:
- A Jenkins build (which compiles Docker images) will **eat all the CPU/RAM**, causing your live app to slow down or crash
- If the server dies, you lose **both** your app AND your monitoring — so you can't even see what happened
- Security: your CI/CD tool (which holds Docker Hub passwords, API keys) should not be on the same machine that faces public traffic

### The Two-Server Solution

```
┌────────────────────────── AWS VPC (10.0.0.0/16) ──────────────────────────┐
│                                                                            │
│   ┌─────────────────────────┐         ┌─────────────────────────┐         │
│   │  EC2-A: APP SERVER      │         │  EC2-B: OPS SERVER      │         │
│   │  (t3.micro)             │         │  (t3.micro)             │         │
│   │                         │         │                         │         │
│   │  ┌───────────────────┐  │  scrape │  ┌───────────────────┐  │         │
│   │  │ Docker Container  │  │◄────────┤  │ Prometheus :9090  │  │         │
│   │  │ FastAPI App       │  │ :30080  │  │ (metrics DB)      │  │         │
│   │  │ Port 30080→8000   │  │ /metrics│  └───────────────────┘  │         │
│   │  └───────────────────┘  │         │  ┌───────────────────┐  │         │
│   │                         │  deploy │  │ Jenkins :8080     │  │         │
│   │  Runs the actual app    │◄────────┤  │ (CI/CD pipeline)  │  │         │
│   │  that calls AI APIs     │  via SSH│  └───────────────────┘  │         │
│   │  every 120 seconds      │         │  ┌───────────────────┐  │         │
│   │                         │         │  │ Grafana :3000     │  │         │
│   └─────────────────────────┘         │  │ (dashboards)      │  │         │
│                                       │  └───────────────────┘  │         │
│                                       └─────────────────────────┘         │
└────────────────────────────────────────────────────────────────────────────┘
```

| Server | Purpose | What Runs | Why Separate |
|--------|---------|-----------|-------------|
| **EC2-A** (App Server) | Runs the production application | Docker container with FastAPI on port `30080` | Dedicated resources for the app; no interference from builds |
| **EC2-B** (Ops Server) | Runs all DevOps tooling | Jenkins (`:8080`), Prometheus (`:9090`), Grafana (`:3000`) via `docker-compose` | Heavy build jobs don't affect the live app; monitoring stays up even if app crashes |

> **Alternative:** If you only have one server, you can run everything on it using docker-compose. Just add the FastAPI service to `docker-compose.yml`. This works for development but is not recommended for production.

### How Data Flows Between Servers

1. **You push code** to GitHub
2. **Jenkins (EC2-B)** detects the change, runs tests, builds a Docker image, pushes to Docker Hub
3. **Jenkins SSHs into EC2-A** and deploys the new container with `docker run`
4. **FastAPI (EC2-A)** starts checking AI providers every 120 seconds, exposing metrics at `/metrics`
5. **Prometheus (EC2-B)** auto-discovers EC2-A using AWS EC2 tags and scrapes `/metrics` every 15 seconds
6. **Grafana (EC2-B)** queries Prometheus and displays real-time dashboards

---

## 🗂️ Project File Structure (22 files)

Every file in this repository has a purpose. Here is what each one does:

```
uptime-monitor/
│
├── app/                              # ── APPLICATION CODE ──
│   ├── main.py                       # FastAPI server (414 lines): background checker loop,
│   │                                 #   REST API endpoints, Prometheus metric exports,
│   │                                 #   retry logic (tenacity), timeout enforcement
│   ├── providers.json                # Pre-configured AI providers (OpenRouter, Gemini, HuggingFace)
│   ├── prompts.json                  # Test prompts with expected answers for validation
│   ├── requirements.txt              # Python dependencies with minimum versions
│   └── .env.example                  # Template for API keys (copy to .env and fill in)
│
├── terraform/                        # ── INFRASTRUCTURE AS CODE ──
│   ├── main.tf                       # Creates: VPC, subnet, internet gateway, 2 EC2 instances
│   ├── iam.tf                        # IAM roles: CloudWatch for App, EC2 Describe + S3 for Ops
│   ├── security_groups.tf            # Firewall rules: which ports are open on which server
│   ├── outputs.tf                    # Prints server IPs and URLs after terraform apply
│   └── .terraform.lock.hcl           # Terraform provider version lock file
│
├── grafana/                          # ── DASHBOARD AUTO-PROVISIONING ──
│   ├── datasource.yml                # Tells Grafana where Prometheus is (auto-configured)
│   ├── dashboard_provider.yml        # Tells Grafana to load dashboards from JSON files
│   └── observatory.json              # The actual Grafana dashboard (all panels pre-built)
│
├── cloudformation/                   # ── AWS BACKUP INFRASTRUCTURE ──
│   └── backup-bucket.yaml            # Creates an S3 bucket for providers.json backups
│
├── tests/                            # ── AUTOMATED TESTS ──
│   └── test_api.py                   # Pytest suite (runs in Jenkins pipeline)
│
├── Dockerfile                        # Builds the FastAPI app container (Python 3.11-slim)
├── docker-compose.yml                # Runs Jenkins + Prometheus + Grafana on the Ops Server
├── prometheus.yml                    # Prometheus config with EC2 dynamic service discovery
├── Jenkinsfile                       # 6-stage CI/CD pipeline definition
├── test_setup.py                     # Manual smoke test: adds providers/prompts via REST API
└── .gitignore                        # Keeps secrets, .env, tfstate out of Git
```

---

## ⚡ Key Engineering Decisions

### 1. Strict 15-Second Client Timeouts
**Problem:** Free-tier AI endpoints sometimes hang for 60+ seconds before responding, blocking the entire background check loop.
**Solution:** Every API checker enforces `timeout=15.0` seconds. If a provider doesn't respond in 15s, we fail fast and move to the next one.

### 2. Automatic Retry with Tenacity
**Problem:** A single network hiccup shouldn't mark a provider as DOWN.
**Solution:** Each checker retries up to **3 times** with a **2-second delay** between attempts before recording a failure. Uses the `tenacity` library.

### 3. Classified Error Metrics
**Problem:** A rate-limit error (429) and a credential error (401) both showed up as the same generic "error" counter.
**Solution:** Errors are now dynamically classified into types: `timeout`, `rate_limit_429`, `auth_401`, `payment_required_402`, `not_found_404`, `generic_internal`. This lets you build a "Top Error Causes" chart in Grafana.

### 4. Dynamic EC2 Service Discovery
**Problem:** When EC2 instances restart, they get new IPs, breaking hardcoded Prometheus targets.
**Solution:** Prometheus uses `ec2_sd_configs` to auto-discover the App Server by its AWS Name tag (`ai-observatory-app`). No manual IP updates ever needed.

---

## 🔧 Exact Versions (Verified on Live Servers)

| Component | Version | Where It Runs |
|-----------|---------|--------------|
| Python | 3.11.15 | Inside FastAPI container |
| FastAPI | 0.136.1 | Inside FastAPI container |
| Uvicorn | 0.47.0 | Inside FastAPI container |
| OpenAI SDK | 2.37.0 | Inside FastAPI container |
| httpx | 0.28.1 | Inside FastAPI container |
| tenacity | 9.1.4 | Inside FastAPI container |
| prometheus-client | 0.25.0 | Inside FastAPI container |
| Docker | 29.1.3 | Both EC2 instances |
| Jenkins | 2.555.2 LTS | Ops Server container |
| Prometheus | 3.11.3 | Ops Server container |
| Grafana | 13.0.1 | Ops Server container |
| Terraform | ≥ 1.5 | Your local machine |
| AWS Provider | ~> 5.0 | Terraform plugin |
| Ubuntu AMI | 22.04 LTS | Both EC2 instances |
| EC2 Instance | t3.micro | Both (free-tier eligible) |

---

## 📡 REST API Reference

The FastAPI app exposes these endpoints (interactive docs at `/docs`):

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check — returns status, uptime, provider/prompt counts |
| `GET` | `/docs` | Interactive Swagger UI for testing all endpoints |
| `GET` | `/metrics` | Prometheus-format metrics (scraped every 15s) |
| `GET` | `/providers` | List all monitored AI providers and their current status |
| `POST` | `/providers` | Add a new provider at runtime (no restart needed) |
| `DELETE` | `/providers/{id}` | Remove a provider |
| `GET` | `/prompts` | List all test prompts |
| `POST` | `/prompts` | Add a new prompt with expected answer |
| `DELETE` | `/prompts/{id}` | Remove a prompt |
| `GET` | `/config` | View current check interval |
| `PUT` | `/config` | Change interval (10–3600 seconds) |
| `POST` | `/simulate/failure/{id}` | Simulate a 3-minute outage for chaos testing |

---

## 🔄 CI/CD Pipeline (6 Stages)

```
 Checkout ──▶ Test ──▶ Security Scan ──▶ Build ──▶ Push ──▶ Deploy
```

| Stage | What It Does | Tools Used |
|-------|-------------|------------|
| **Checkout** | Clones latest code from GitHub | Git |
| **Test** | Creates virtualenv, installs deps, runs `pytest` | Python, pytest |
| **Security Scan** | Checks Python deps for CVEs + scans Docker base image | `safety`, `trivy` |
| **Build** | `docker build` with build-number tag | Docker |
| **Push** | Pushes image to Docker Hub (`adityapichikala/ai-observatory`) | Docker Hub |
| **Deploy** | SSHs into EC2-A, stops old container, runs new one, backs up to S3 | SSH, AWS CLI |

---

## 🚀 Full Implementation Guide

### Prerequisites

| Requirement | How to Get It | Alternative |
|-------------|--------------|-------------|
| AWS Account + CLI | `aws configure` with access key | Any cloud: GCP (`gcloud`), Azure (`az`) |
| Terraform ≥ 1.5 | [terraform.io/downloads](https://developer.hashicorp.com/terraform/downloads) | AWS CloudFormation, Pulumi |
| Docker | [docker.com](https://docker.com) | Podman |
| Docker Hub account | [hub.docker.com](https://hub.docker.com) | GitHub Container Registry, AWS ECR |
| EC2 Key Pair (us-east-1) | AWS Console → EC2 → Key Pairs | Generate with `ssh-keygen` |
| OpenRouter API key | [openrouter.ai/keys](https://openrouter.ai/settings/keys) | Groq, Together AI |
| Gemini API key | [aistudio.google.com](https://aistudio.google.com/apikey) | OpenAI, Anthropic |
| HuggingFace token | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | Replicate |

### Step 1 — Test Locally First

```bash
# Clone the repo
git clone https://github.com/adityapichikala/uptime-monitor.git
cd uptime-monitor/app

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up your API keys
cp .env.example .env
# Edit .env and paste your actual keys

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Verify these URLs in your browser:
- `http://localhost:8000` → Health check JSON
- `http://localhost:8000/docs` → Swagger UI
- `http://localhost:8000/metrics` → Prometheus metrics

Run the smoke test (separate terminal):
```bash
cd uptime-monitor
python test_setup.py
```

### Step 2 — Provision AWS Infrastructure

```bash
cd terraform

terraform init
terraform plan -var="key_name=YOUR_KEY" -var="your_ip=YOUR_IP/32"
terraform apply -var="key_name=YOUR_KEY" -var="your_ip=YOUR_IP/32"
# Type "yes" when prompted

# Save the output IPs
terraform output
```

This creates: 1 VPC, 1 public subnet, 1 internet gateway, 2 EC2 instances (t3.micro), security groups, and IAM roles.

### Step 3 — Verify the Ops Stack (EC2-B)

The Ops Server auto-starts via `user_data`. SSH in to verify:

```bash
ssh -i "your-key.pem" ubuntu@<OPS_SERVER_IP>
cd /home/ubuntu/uptime-monitor
docker-compose ps   # Should show: jenkins, prometheus, grafana
```

### Step 4 — Configure Jenkins

1. Open `http://<OPS_IP>:8080`
2. Get initial password: `docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword`
3. Install suggested plugins → Create admin user
4. Add these credentials (Manage Jenkins → Credentials → Global):

| Credential ID | Type | Value |
|--------------|------|-------|
| `dockerhub-creds` | Username/Password | Your Docker Hub login |
| `openrouter-api-key` | Secret text | Your OpenRouter API key |
| `gemini-api-key` | Secret text | Your Gemini API key |
| `hf-api-key` | Secret text | Your HuggingFace token |
| `ec2-ssh-key-b64` | Secret text | Base64-encoded EC2 private key |

5. Create Pipeline job → SCM: Git → URL: `https://github.com/adityapichikala/uptime-monitor.git` → Script Path: `Jenkinsfile`

### Step 5 — Verify Everything

| Service | URL | Expected Result |
|---------|-----|----------------|
| FastAPI | `http://<APP_IP>:30080` | JSON health response |
| Swagger | `http://<APP_IP>:30080/docs` | Interactive API docs |
| Prometheus | `http://<OPS_IP>:9090/targets` | `ai-observatory-dynamic` target = UP |
| Grafana | `http://<OPS_IP>:3000` | Login (admin/admin), dashboard with live data |
| Jenkins | `http://<OPS_IP>:8080` | Pipeline job visible and buildable |

---

## 🔒 Security Measures

| Measure | Implementation |
|---------|---------------|
| Rate Limiting | 10 requests/minute per IP via SlowAPI |
| Secret Management | API keys passed as env vars, never hardcoded |
| IAM Least Privilege | App: CloudWatch only; Ops: EC2 Describe + S3 only |
| Container Scanning | Trivy scans for HIGH/CRITICAL CVEs in CI |
| Dependency Scanning | Safety checks Python packages for known vulnerabilities |
| Network Isolation | Security groups restrict access per port |
| S3 Backup Encryption | AES-256 server-side encryption on backup bucket |

---

## 🧹 Cleanup

To avoid AWS charges when done:
```bash
cd terraform
terraform destroy -var="key_name=YOUR_KEY" -var="your_ip=YOUR_IP/32"
```

---

<div align="center">

**INT377 — Cloud Computing & Automation**

*Aditya Pichikala*

</div>
