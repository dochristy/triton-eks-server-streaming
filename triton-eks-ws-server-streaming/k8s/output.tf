# outputs.tf
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "The CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "The name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster for the OpenID Connect identity provider"
  value       = module.eks.cluster_oidc_issuer_url
}

output "nat_public_ips" {
  description = "List of public Elastic IPs created for NAT Gateway"
  value       = module.vpc.nat_public_ips
}

output "triton_endpoints" {
  description = "Triton Server endpoints"
  value = {
    http      = "${kubernetes_service.triton.status[0].load_balancer.0.ingress.0.hostname}:8000"
    grpc      = "${kubernetes_service.triton.status[0].load_balancer.0.ingress.0.hostname}:8001"
    metrics   = "${kubernetes_service.triton.status[0].load_balancer.0.ingress.0.hostname}:8002"
    websocket = "ws://${kubernetes_service.triton.status[0].load_balancer.0.ingress.0.hostname}:8080"
  }
}
