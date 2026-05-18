<div align="center">

# 🔭 AI API Observatory

### Real-Time AI Provider Health, Latency, Cost & Resilient Uptime Monitoring

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform&logoColor=white)](https://terraform.io)
[![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-D24939?logo=jenkins&logoColor=white)](https://jenkins.io)
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?logo=grafana&logoColor=white)](https://grafana.com)

</div>

---

## 📖 About This Project

**AI API Observatory** is a production-grade DevOps project designed to continuously observe, validate, and measure multiple LLM API providers in real-time. It checks whether AI endpoints like **OpenRouter (Meta Llama 3.3)**, **Google Gemini (2.5 Flash)**, and **HuggingFace (BART-CNN)** are online, how fast they respond, how many tokens they consume, how much each call costs, and whether the model's response matches our strict semantic expectations.

### Why does this matter?
If you're building products that depend on third-party AI APIs, you need to know:
* 🟢 **Uptime:** Is the provider alive right now?
* ⏱️ **Latency:** How slow are responses today?
* 💸 **Cost Tracking:** Am I burning through my budget?
* 🎯 **Response Validity:** Is the model giving garbage answers?

This project answers these questions using a fully automated DevOps pipeline — from infrastructure provisioning with Terraform, to automated builds via Jenkins, to robust monitoring using Prometheus & Grafana.

---

## 📐 Architecture Overview

The platform is deployed inside a dedicated, isolated custom VPC on AWS spanning **two EC2 instances**:

```
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

### Server Component Breakdown
* 🖥️ **EC2-A (App Server):** Runs the lightweight, high-performance **FastAPI backend** inside a production-hardened Docker container exposed on port `30080`.
* 🛠️ **EC2-B (Ops Server):** Runs the core DevOps and monitoring orchestration engine, managing **Jenkins** for builds/deployments, **Prometheus** for metrics collection, and **Grafana** for rich data visualization.

---

## ⚡ 4 Key Resiliency & Observability Upgrades

This system implements four state-of-the-art updates that elevate it to a professional-grade DevOps project:

1. **⏱️ Strict Client Timeouts:** Avoids pipeline lockups by enforcing a hard 15-second client timeout on all API checker requests (preventing stalled endpoints from blocking the background queue).
2. **🔄 Tenacity Retry Decoupling:** Implemented transient error handling. The checker engine automatically retries failing calls **3 times with a 2-second backoff delay** before marking an API provider as `DOWN`.
3. **🏷️ Metric Error Classification:** Upgraded Prometheus counters to track `error_type` as a label:
   ```promql
   api_error_total{error_type="rate_limit_429", provider="Gemini"} 1.0
   ```
   *Dynamically categorizes failures as `timeout`, `rate_limit_429`, `auth_401`, `payment_required_402`, or `generic_internal`.*
4. **🚨 SLA Alert Rules:** Configured Alertmanager guidelines that fire critical alarms (`AIProviderDown`) if a provider remains unavailable for more than **5 consecutive minutes**.

---

## 🗂️ Clean Project Directory Structure

Every useless or legacy configuration file has been cleanly pruned to keep this repository pristine for demo presentation:

```
uptime-monitor/
├── app/                          # ── FastAPI Core Code ──
│   ├── main.py                   # Async backend and background evaluation loop
│   ├── providers.json            # Dynamic AI API provider details
│   ├── prompts.json              # Custom evaluation prompts & answers
│   ├── requirements.txt          # Production dependencies (FastAPI, tenacity, etc.)
│   └── .env.example              # Secret key template
│
├── terraform/                    # ── Infrastructure as Code (IaC) ──
│   ├── main.tf                   # VPC, public subnet, EC2 allocations
│   ├── iam.tf                    # IAM least-privilege security policies
│   ├── security_groups.tf        # Pin-pointed firewall access rules
│   └── outputs.tf                # Deploy URL and IP variables
│
├── grafana/                      # ── Dashboard Provisioning ──
│   ├── datasource.yml            # Auto-registered Prometheus connector
│   ├── dashboard_provider.yml    # Auto-load dashboard configs
│   └── observatory.json          # Premium Grafana JSON dashboard model
│
├── cloudformation/               # ── AWS Backup Templates ──
│   └── backup-bucket.yaml        # S3 storage backup configuration
│
├── Dockerfile                    # Container blueprint for the app
├── docker-compose.yml            # Jenkins, Prometheus, and Grafana orchestrator
├── prometheus.yml                # Dynamic EC2 Service Discovery rules
├── Jenkinsfile                   # Hardened 6-Stage CI/CD automation pipeline
├── test_setup.py                 # Interactive API test setup script
└── tests/                        # ── Automated Unit Testing ──
    └── test_api.py               # API endpoint pytests
```

---

## 🔄 The CI/CD Automation Pipeline

When code is pushed to the repository, Jenkins triggers the following robust automated pipeline:

```
 ┌──────────┐    ┌──────────┐    ┌───────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
 │ Checkout │───▶│   Test   │───▶│ Security Scan │───▶│  Build   │───▶│   Push   │───▶│  Deploy  │
 │ (git)    │    │ (pytest) │    │(trivy+safety) │    │ (docker) │    │(DockerHub│    │ (Docker) │
 └──────────┘    └──────────┘    └───────────────┘    └──────────┘    └──────────┘    └──────────┘
```

1. **Checkout:** Pulls the newest code branches from GitHub.
2. **Test:** Creates a clean virtual environment, installs dependencies, and runs `pytest`.
3. **Security Scan:** Performs dependency security checks (`safety`) and scans base images (`trivy`).
4. **Build:** Compiles the optimized application image tagged with the corresponding build number.
5. **Push:** Securely uploads the packaged image to Docker Hub.
6. **Deploy:** Automatically connects to the App Server, performs a seamless rollout, and backs up runtime configurations to AWS S3.

---

## 🚀 How to Run & Verify the Observability Stack

### Phase 1: Local Evaluation (Smoke Test)
```bash
# Clone the repository
git clone https://github.com/adityapichikala/uptime-monitor.git
cd uptime-monitor/app

# Set up environment variables
cp .env.example .env
# Open .env and add your valid API Keys

# Start the server locally
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

In a separate terminal, execute the local validation script:
```bash
python test_setup.py
```

### Phase 2: Prometheus Service Discovery & Scrape Check
1. Access the **Prometheus Dashboard** at: `http://<OPS_SERVER_IP>:9090/targets`
2. You will see `ai-observatory-dynamic` marked as **UP (1/1 active targets healthy)**.
3. This dynamic discovery automatically targets `http://<APP_SERVER_IP>:30080/metrics` based on AWS EC2 Resource tags!

### Phase 3: Display Dashboards in Grafana
1. Navigate to **Grafana**: `http://<OPS_SERVER_IP>:3000` *(Login: `admin` / `admin`)*
2. Select the **AI API Observatory** Dashboard.
3. View latency, validity percentages, and granular error charts in real-time!

---

<div align="center">

**INT377 — Cloud Computing & Automation Capstone**

*Aditya Pichikala*

</div>
