# ─── EC2-A: App Server Security Group ────────────────────────────────────────

resource "aws_security_group" "app_sg" {
  name        = "ai-observatory-app-sg"
  description = "Security group for the App Server (EC2-A / k3s)"
  vpc_id      = aws_vpc.main.id

  # SSH from anywhere temporarily
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NodePort for FastAPI — from your IP + Ops SG
  ingress {
    description = "FastAPI NodePort from your IP"
    from_port   = 30080
    to_port     = 30080
    protocol    = "tcp"
    cidr_blocks = [var.your_ip]
  }

  ingress {
    description     = "FastAPI NodePort from Ops Server"
    from_port       = 30080
    to_port         = 30080
    protocol        = "tcp"
    security_groups = [aws_security_group.ops_sg.id]
  }

  # k3s API (6443) — only from Ops SG for Jenkins kubectl
  ingress {
    description     = "k3s API from Ops Server only"
    from_port       = 6443
    to_port         = 6443
    protocol        = "tcp"
    security_groups = [aws_security_group.ops_sg.id]
  }

  # All outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "ai-observatory-app-sg"
    Project     = "ai-observatory"
    Environment = "student"
  }
}

# ─── EC2-B: Ops Server Security Group ────────────────────────────────────────

resource "aws_security_group" "ops_sg" {
  name        = "ai-observatory-ops-sg"
  description = "Security group for the Ops Server (EC2-B)"
  vpc_id      = aws_vpc.main.id

  # SSH from anywhere temporarily
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Jenkins from anywhere
  ingress {
    description = "Jenkins UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Prometheus
  ingress {
    description = "Prometheus UI"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = [var.your_ip]
  }

  # Grafana
  ingress {
    description = "Grafana UI"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.your_ip]
  }

  # All outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "ai-observatory-ops-sg"
    Project     = "ai-observatory"
    Environment = "student"
  }
}
