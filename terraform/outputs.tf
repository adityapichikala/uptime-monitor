output "app_server_public_ip" {
  description = "Public IP of EC2-A (App Server / k3s)"
  value       = aws_instance.app_server.public_ip
}

output "app_server_private_ip" {
  description = "Private IP of EC2-A (use in prometheus.yml)"
  value       = aws_instance.app_server.private_ip
}

output "ops_server_public_ip" {
  description = "Public IP of EC2-B (Ops Server)"
  value       = aws_instance.ops_server.public_ip
}

output "fastapi_url" {
  description = "FastAPI app URL"
  value       = "http://${aws_instance.app_server.public_ip}:30080"
}

output "fastapi_docs_url" {
  description = "FastAPI Swagger docs"
  value       = "http://${aws_instance.app_server.public_ip}:30080/docs"
}

output "jenkins_url" {
  description = "Jenkins UI"
  value       = "http://${aws_instance.ops_server.public_ip}:8080"
}

output "prometheus_url" {
  description = "Prometheus UI"
  value       = "http://${aws_instance.ops_server.public_ip}:9090"
}

output "grafana_url" {
  description = "Grafana UI (admin/admin)"
  value       = "http://${aws_instance.ops_server.public_ip}:3000"
}

output "prometheus_scrape_target" {
  description = "Replace EC2_A_PRIVATE_IP in prometheus.yml with this value"
  value       = aws_instance.app_server.private_ip
}
