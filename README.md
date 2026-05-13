<div align="center">

# 🔭 AI API Observatory

### Real-Time AI Provider Health, Latency, Cost & Validity Monitoring

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-k3s-326CE5?logo=kubernetes&logoColor=white)](https://k3s.io)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform&logoColor=white)](https://terraform.io)
[![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-D24939?logo=jenkins&logoColor=white)](https://jenkins.io)
[![Docker](https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?logo=grafana&logoColor=white)](https://grafana.com)

</div>

---

## 📖 About This Project

**AI API Observatory** is a production-grade DevOps project that continuously monitors multiple AI APIs in real time. It checks whether AI providers like **Groq**, **Google Gemini**, and **HuggingFace** are online, how fast they respond, how many tokens they consume, how much each call costs, and whether the AI's answer is actually correct.

### Why does this matter?

If you're building an application that depends on AI APIs, you need to know:
- **Is my AI provider even up right now?** (uptime monitoring)
- **How slow is it today?** (latency tracking)
- **Am I burning through tokens?** (cost monitoring)
- **Is the AI giving garbage answers?** (response validity)

This project answers all of those questions with a fully automated pipeline — from writing code to deploying it on AWS, with CI/CD, container orchestration, and real-time dashboards.

### What does it demonstrate?

This is a complete **end-to-end DevOps pipeline** covering:

| Skill | How it's used |
|-------|--------------|
| **Python Development** | FastAPI async backend with background monitoring loop |
| **Containerization** | Dockerfile for the app, docker-compose for the ops stack |
| **Container Orchestration** | Kubernetes (k3s) with Deployments, Services, HPA, PVC |
| **Infrastructure as Code** | Terraform provisions the entire AWS infrastructure |
| **CI/CD Automation** | Jenkins pipeline: test → scan → build → push → deploy |
| **Monitoring & Observability** | Prometheus scrapes metrics, Grafana visualizes them |
| **Security** | Trivy container scanning, Safety dependency checks, IAM least-privilege |
| **Cloud Computing** | AWS VPC, EC2, IAM, Security Groups, S3 backups |

---

## 📐 Architecture

The system runs on **two EC2 instances** inside a custom VPC on AWS:

```
┌─────────────────────────────── AWS Cloud (us-east-1) ────────────────────────────────┐
│                                                                                       │
│  ┌──────────────────────── VPC 10.0.0.0/16 ────────────────────────┐                  │
│  │                                                                  │                  │
│  │  ┌──────────────── Public Subnet 10.0.1.0/24 ──────────────┐    │                  │
│  │  │                                                          │    │                  │
│  │  │  ┌─────────────────────────┐  ┌────────────────────────┐ │    │                  │
│  │  │  │  EC2-A: App Server      │  │  EC2-B: Ops Server     │ │    │                  │
│  │  │  │  (t3.micro)             │  │  (t3.micro)            │ │    │                  │
│  │  │  │                         │  │                        │ │    │                  │
│  │  │  │  ┌───────────────────┐  │  │  ┌──────────────────┐  │ │    │                  │
│  │  │  │  │  k3s Cluster      │  │  │  │  Jenkins :8080   │  │ │    │                  │
│  │  │  │  │                   │  │  │  │  (CI/CD)         │  │ │    │                  │
│  │  │  │  │  Pod 1: FastAPI   │  │  │  └──────────────────┘  │ │    │                  │
│  │  │  │  │  Pod 2: FastAPI   │◄─┼──┼──┐                     │ │    │                  │
│  │  │  │  │  Pod 3: FastAPI   │  │  │  │ ┌──────────────────┐│ │    │                  │
│  │  │  │  │                   │  │  │  │ │Prometheus :9090  ││ │    │                  │
│  │  │  │  │  NodePort :30080  │  │  │  └─│(scrapes /metrics)││ │    │                  │
│  │  │  │  └───────────────────┘  │  │    └──────────────────┘│ │    │                  │
│  │  │  │                         │  │    ┌──────────────────┐│ │    │                  │
│  │  │  │  HPA: 1-5 pods         │  │    │ Grafana :3000    ││ │    │                  │
│  │  │  │  PVC: 100Mi storage    │  │    │ (dashboards)     ││ │    │                  │
│  │  │  │                         │  │    └──────────────────┘│ │    │                  │
│  │  │  └─────────────────────────┘  └────────────────────────┘ │    │                  │
│  │  └──────────────────────────────────────────────────────────┘    │                  │
│  └──────────────────────────────────────────────────────────────────┘                  │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘

         │                              │                              │
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌────────────┐                ┌─────────────┐
   │  Groq API │                 │ Gemini API │                │HuggingFace  │
   │ Llama3-8B │                 │ 1.5 Flash  │                │   GPT-2     │
   └───────────┘                 └────────────┘                └─────────────┘
```

### How the two servers work together

| Server | Role | What runs on it |
|--------|------|-----------------|
| **EC2-A** (App Server) | Runs the actual application | k3s cluster with FastAPI pods, NodePort service on :30080 |
| **EC2-B** (Ops Server) | Runs the DevOps tooling | Jenkins (CI/CD), Prometheus (metrics), Grafana (dashboards) |

**Data flow:**
1. FastAPI pods on EC2-A check AI providers every 120 seconds
2. Each check records latency, tokens, cost, and validity as Prometheus metrics
3. Prometheus on EC2-B auto-discovers EC2-A using AWS EC2 tags (no manual IP needed)
4. Prometheus scrapes the `/metrics` endpoint on port 30080
5. Grafana queries Prometheus and displays real-time dashboards

---

## 🗂️ Project Structure

```
uptime-monitor/
│
├── app/                          # ── Application Layer ──
│   ├── main.py                   # FastAPI server + async background checker
│   ├── providers.json            # Pre-configured AI provider definitions
│   ├── prompts.json              # Test prompts with expected answers
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Environment variable template
│
├── k8s/                          # ── Kubernetes Manifests ──
│   ├── deployment.yaml           # Deployment (3 replicas) + PVC
│   ├── service.yaml              # NodePort Service (:30080)
│   └── hpa.yaml                  # Horizontal Pod Autoscaler (1-5 pods)
│
├── terraform/                    # ── Infrastructure as Code ──
│   ├── main.tf                   # VPC, subnets, EC2 instances
│   ├── iam.tf                    # IAM roles and policies
│   ├── security_groups.tf        # Firewall rules
│   └── outputs.tf                # Output IPs and URLs
│
├── grafana/
│   └── datasource.yml            # Auto-provisioned Prometheus datasource
│
├── Dockerfile                    # Container image for the FastAPI app
├── docker-compose.yml            # Ops stack (Jenkins + Prometheus + Grafana)
├── prometheus.yml                # Prometheus config with EC2 service discovery
├── Jenkinsfile                   # 6-stage CI/CD pipeline
├── test_setup.py                 # Smoke test script (10 checks)
└── tests/
    └── test_api.py               # Pytest suite
```

---

## 🔄 CI/CD Pipeline (Jenkinsfile)

When you push code to GitHub, Jenkins automatically runs this 6-stage pipeline:

```
 ┌──────────┐    ┌──────────┐    ┌───────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
 │ Checkout │───▶│   Test   │───▶│ Security Scan │───▶│  Build   │───▶│   Push   │───▶│  Deploy  │
 │ (git)    │    │ (pytest) │    │(trivy+safety) │    │ (docker) │    │(DockerHub│    │(kubectl) │
 └──────────┘    └──────────┘    └───────────────┘    └──────────┘    └──────────┘    └──────────┘
```

1. **Checkout** — Pulls latest code from GitHub
2. **Test** — Creates virtualenv, installs deps, runs `pytest`
3. **Security Scan** — `safety` checks Python deps, `trivy` scans base image
4. **Build** — `docker build` with build number tag
5. **Push** — Pushes image to Docker Hub as `adityapichikala/ai-observatory`
6. **Deploy** — Creates K8s secrets, `kubectl apply`, rolling update, S3 backup

---

## 📡 API Reference

The FastAPI app exposes these endpoints:

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `GET` | `/` | Health check — returns status, version, provider/prompt counts |
| `GET` | `/docs` | Interactive Swagger UI for testing all endpoints |
| `GET` | `/providers` | List all monitored AI providers and their status |
| `POST` | `/providers` | Add a new AI provider to monitor |
| `DELETE` | `/providers/{id}` | Stop monitoring a provider |
| `GET` | `/prompts` | List all test prompts |
| `POST` | `/prompts` | Add a new test prompt with expected answer |
| `DELETE` | `/prompts/{id}` | Remove a prompt |
| `GET` | `/config` | View current check interval |
| `PUT` | `/config` | Change check interval (10–3600 seconds) |
| `POST` | `/simulate/failure/{id}` | Simulate a 3-minute provider outage for testing |
| `GET` | `/metrics` | Prometheus metrics (api_up, latency, tokens, cost, validity) |

---

## 📈 Metrics Tracked

Every 120 seconds, the app checks each AI provider and records:

| Metric | What it measures |
|--------|-----------------|
| `api_up` | Is the provider reachable? (1 = yes, 0 = no) |
| `api_response_time_seconds` | How long did the API call take? |
| `api_tokens_used` | How many tokens were consumed? |
| `api_cost_usd` | Estimated cost based on provider pricing |
| `api_response_valid` | Did the AI return the expected answer? |
| `api_error_total` | Running count of errors per provider |
| `api_requests_total` | Running count of all requests per provider |

---

## 🚀 How to Deploy This Project (Step by Step)

### What you need before starting

| Requirement | How to get it |
|-------------|---------------|
| AWS account with CLI configured | Run `aws configure` with your access key |
| Terraform ≥ 1.5 | Download from [terraform.io](https://developer.hashicorp.com/terraform/downloads) |
| Docker installed | Download from [docker.com](https://docker.com) |
| Docker Hub account | Sign up at [hub.docker.com](https://hub.docker.com) |
| EC2 Key Pair in **us-east-1** | AWS Console → EC2 → Key Pairs → Create |
| Your public IP | Visit [whatismyip.com](https://whatismyip.com) |
| AI API keys (Groq, Gemini, HuggingFace) | Sign up at each provider's website |

---

### Phase 1 — Test Locally First

Before deploying to AWS, verify the app works on your machine:

```bash
# Clone the repo
git clone https://github.com/adityapichikala/uptime-monitor.git
cd uptime-monitor

# Create virtual environment
cd app
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup your API keys
cp .env.example .env
# Edit .env and paste your actual API keys

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Verify these URLs work:**
- http://localhost:8000 → Health check JSON
- http://localhost:8000/docs → Swagger UI
- http://localhost:8000/metrics → Prometheus metrics

**Run the smoke test** (in a separate terminal):
```bash
cd uptime-monitor
python test_setup.py
```

This adds all 3 providers + a test prompt and verifies all 10 endpoints.

---

### Phase 2 — Provision AWS Infrastructure with Terraform

This creates the entire AWS environment with one command:

```bash
cd terraform

# Download the AWS provider
terraform init

# Preview what will be created (no changes yet)
terraform plan -var="key_name=YOUR_KEY" -var="your_ip=YOUR_IP/32"

# Create everything
terraform apply -var="key_name=YOUR_KEY" -var="your_ip=YOUR_IP/32"
# Type "yes" when prompted
```

> Replace `YOUR_KEY` with your EC2 key pair name and `YOUR_IP` with your public IP.

**What Terraform creates:**
- 1 VPC with public subnet and internet gateway
- 2 EC2 instances (t3.micro — free tier eligible)
- Security groups locking access to your IP only
- IAM roles with least-privilege policies
- k3s auto-installs on EC2-A, Docker auto-installs on EC2-B

**Save the output IPs** — you'll need them:
```bash
terraform output
```

---

### Phase 3 — Build & Push the Docker Image

```bash
# Back in the project root
cd ..

# Login to Docker Hub
docker login

# Build the app image
docker build -t adityapichikala/ai-observatory:latest .

# Push to Docker Hub (so EC2 can pull it)
docker push adityapichikala/ai-observatory:latest
```

---

### Phase 4 — Deploy the App on EC2-A (k3s)

SSH into the App Server:
```bash
ssh -i "your-key.pem" ubuntu@<APP_SERVER_IP>
```

Wait 2–3 minutes after Terraform for k3s to finish installing, then:

```bash
# Verify k3s is running
sudo kubectl get nodes    # Should show "Ready"

# Create Kubernetes secrets with your API keys
sudo kubectl create secret generic ai-observatory-secrets \
  --from-literal=GROQ_API_KEY="your_groq_key" \
  --from-literal=GEMINI_API_KEY="your_gemini_key" \
  --from-literal=HF_API_KEY="your_hf_key"

# Clone the repo and deploy
git clone https://github.com/adityapichikala/uptime-monitor.git
cd uptime-monitor
sudo kubectl apply -f k8s/

# Watch pods come up (wait until all show "Running")
sudo kubectl get pods -w

# Test it
curl http://localhost:30080/
```

---

### Phase 5 — Start the Ops Stack on EC2-B

SSH into the Ops Server:
```bash
ssh -i "your-key.pem" ubuntu@<OPS_SERVER_IP>
```

The user_data script should have already started everything. Verify:
```bash
cd /home/ubuntu/uptime-monitor
docker-compose ps        # Should show jenkins, prometheus, grafana

# If not running, start manually:
sudo docker-compose up -d
```

---

### Phase 6 — Configure Jenkins

1. Open `http://<OPS_IP>:8080` in your browser
2. Get the initial password:
   ```bash
   docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
3. Install suggested plugins → Create admin user
4. Add credentials (Manage Jenkins → Credentials → Global):
   - `dockerhub-creds` (Username/Password) — Docker Hub login
   - `groq-api-key` (Secret text) — Groq API key
   - `gemini-api-key` (Secret text) — Gemini API key
   - `hf-api-key` (Secret text) — HuggingFace token
   - `ec2-kubeconfig` (Secret text) — k3s kubeconfig from EC2-A
5. Get kubeconfig from EC2-A:
   ```bash
   # On EC2-A
   sudo cat /etc/rancher/k3s/k3s.yaml
   # Copy entire content, replace 127.0.0.1 with EC2-A's private IP
   ```
6. Create Pipeline job → SCM: Git → URL: `https://github.com/adityapichikala/uptime-monitor.git` → Script Path: `Jenkinsfile`

---

### Phase 7 — Verify Everything Works

| Service | URL | What to check |
|---------|-----|---------------|
| **FastAPI** | `http://<APP_IP>:30080` | Returns health JSON |
| **Swagger** | `http://<APP_IP>:30080/docs` | Interactive API docs |
| **Prometheus** | `http://<OPS_IP>:9090/targets` | Shows `ai-observatory-dynamic` target as UP |
| **Grafana** | `http://<OPS_IP>:3000` | Login with admin/admin, Prometheus datasource auto-configured |
| **Jenkins** | `http://<OPS_IP>:8080` | Pipeline job visible |

---

## 🔒 Security

- **Rate Limiting** — Max 10 req/min per IP via SlowAPI
- **K8s Secrets** — API keys injected as environment variables, never hardcoded
- **IAM Least Privilege** — App role: CloudWatch only; Ops role: EC2 Describe + S3 only
- **Container Scanning** — Trivy scans for HIGH/CRITICAL CVEs in CI
- **Dependency Scanning** — Safety checks Python packages for known vulnerabilities
- **Network Isolation** — Security groups restrict SSH/UI access to your IP only

---

## 🧹 Cleanup

To avoid AWS charges, destroy everything when done:

```bash
cd terraform
terraform destroy -var="key_name=YOUR_KEY" -var="your_ip=YOUR_IP/32"
```

---

## ⚙️ Tech Stack Summary

| Layer | Tool | Version |
|-------|------|---------|
| Language | Python | 3.11 |
| Framework | FastAPI | 0.111+ |
| Container | Docker | Latest |
| Orchestration | Kubernetes (k3s) | Latest |
| IaC | Terraform | ≥ 1.5 |
| CI/CD | Jenkins | 2.440.3 LTS |
| Metrics | Prometheus | Latest |
| Dashboards | Grafana | Latest |
| Cloud | AWS (us-east-1) | EC2 t3.micro |

---

<div align="center">

**Built for INT377 — Cloud Computing & Automation**

*Aditya Pichikala*

</div>
