terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.aws_region
}

# ─── Variables ────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region"
  default     = "ap-south-1"
}

variable "key_name" {
  description = "EC2 SSH key pair name"
  type        = string
}

variable "your_ip" {
  description = "Your public IP in CIDR notation (e.g. 203.0.113.5/32)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repo URL for uptime-monitor"
  default     = "https://github.com/adityapichikala/uptime-monitor.git"
}

variable "ami_id" {
  description = "Ubuntu 22.04 AMI for ap-south-1"
  default     = "ami-0f5ee92e2d63afc18"
}

# ─── VPC & Networking ────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "ai-observatory-vpc"
    Project     = "ai-observatory"
    Environment = "student"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "ai-observatory-igw"
    Project     = "ai-observatory"
    Environment = "student"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name        = "ai-observatory-public-subnet"
    Project     = "ai-observatory"
    Environment = "student"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = "ai-observatory-public-rt"
    Project     = "ai-observatory"
    Environment = "student"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ─── EC2-A: App Server (k3s) ─────────────────────────────────────────────────

resource "aws_instance" "app_server" {
  ami                    = var.ami_id
  instance_type          = "t2.micro"
  key_name               = var.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.app_profile.name

  user_data = <<-EOF
    #!/bin/bash
    set -e
    fallocate -l 1G /swapfile
    chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    apt-get update -y
    apt-get install -y curl git
    curl -sfL https://get.k3s.io | sh -
    systemctl enable k3s
    sleep 30
    mkdir -p /home/ubuntu/.kube
    cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
    chown ubuntu:ubuntu /home/ubuntu/.kube/config
    PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
    sed -i "s/127.0.0.1/$PRIVATE_IP/g" /home/ubuntu/.kube/config
  EOF

  tags = {
    Name        = "ai-observatory-app"
    Project     = "ai-observatory"
    Environment = "student"
  }
}

# ─── EC2-B: Ops Server (Jenkins + Prometheus + Grafana) ───────────────────────

resource "aws_instance" "ops_server" {
  ami                    = var.ami_id
  instance_type          = "t2.micro"
  key_name               = var.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ops_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ops_profile.name

  user_data = <<-EOF
    #!/bin/bash
    set -e
    fallocate -l 1G /swapfile
    chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    apt-get update -y
    apt-get install -y docker.io docker-compose git awscli
    usermod -aG docker ubuntu
    systemctl enable docker && systemctl start docker
    cd /home/ubuntu
    git clone ${var.github_repo} || true
    cd uptime-monitor
    docker-compose up -d
  EOF

  tags = {
    Name        = "ai-observatory-ops"
    Project     = "ai-observatory"
    Environment = "student"
  }
}
