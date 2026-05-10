# ─── IAM Role for EC2-A (App Server) ──────────────────────────────────────────

resource "aws_iam_role" "app_role" {
  name = "ai-observatory-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = "ai-observatory"
    Environment = "student"
  }
}

# ─── CloudWatch Logs Policy ──────────────────────────────────────────────────

resource "aws_iam_role_policy" "cloudwatch_policy" {
  name = "ai-observatory-cloudwatch"
  role = aws_iam_role.app_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}


# ─── Instance Profile ────────────────────────────────────────────────────────

resource "aws_iam_instance_profile" "app_profile" {
  name = "ai-observatory-app-profile"
  role = aws_iam_role.app_role.name
}

# ─── IAM Role for EC2-B (Ops Server) ──────────────────────────────────────────
# Prometheus needs ec2:DescribeInstances to auto-discover scrape targets.

resource "aws_iam_role" "ops_role" {
  name = "ai-observatory-ops-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = "ai-observatory"
    Environment = "student"
  }
}

# ─── EC2 Describe Policy (for Prometheus SD) ─────────────────────────────────

resource "aws_iam_role_policy" "ec2_describe_policy" {
  name = "ai-observatory-ec2-describe"
  role = aws_iam_role.ops_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

# ─── S3 Backup Write Policy (for Ops Server) ─────────────────────────────────

resource "aws_iam_role_policy" "ops_s3_backup" {
  name = "ai-observatory-ops-s3-write"
  role = aws_iam_role.ops_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:ListBucket"]
      Resource = ["arn:aws:s3:::uptime-backup-*", "arn:aws:s3:::uptime-backup-*/*"]
    }]
  })
}

# ─── Ops Instance Profile ────────────────────────────────────────────────────

resource "aws_iam_instance_profile" "ops_profile" {
  name = "ai-observatory-ops-profile"
  role = aws_iam_role.ops_role.name
}
