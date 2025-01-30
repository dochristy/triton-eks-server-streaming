# kubernetes.tf
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

resource "kubernetes_service_account" "triton" {
  metadata {
    name = "triton-service-account"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.eks_s3_access.arn
    }
  }
}

resource "kubernetes_deployment" "triton" {
  metadata {
    name = "triton-server"
  }
  spec {
    replicas = 1
    selector {
      match_labels = {
        app = "triton-server"
      }
    }
    template {
      metadata {
        labels = {
          app = "triton-server"
        }
      }
      spec {
        service_account_name = "triton-service-account"

        container {
          name  = "triton-server"
          image = "${var.account_id}.dkr.ecr.us-east-1.amazonaws.com/websocket-pipeline:latest"

          args = [
            "tritonserver",
            "--model-repository=s3://dry-bean-bucket-c/models",
            "--http-port=8000",
            "--grpc-port=8001",
            "--metrics-port=8002"
          ]

          env {
            name  = "AWS_REGION"
            value = "us-east-1"
          }

          env {
            name  = "AWS_SDK_LOAD_CONFIG"
            value = "1"
          }

          env {
            name  = "NVIDIA_VISIBLE_DEVICES"
            value = "none"
          }

          port {
            container_port = 8000
            name           = "http"
          }
          port {
            container_port = 8001
            name           = "grpc"
          }
          port {
            container_port = 8002
            name           = "metrics"
          }
          port {
            container_port = 8080
            name           = "websocket"
          }

          startup_probe {
            http_get {
              path = "/v2/health/ready"
              port = 8000
            }
            initial_delay_seconds = 10
            period_seconds        = 5
            failure_threshold     = 30
          }

          readiness_probe {
            http_get {
              path = "/v2/health/ready"
              port = 8000
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
          }

          liveness_probe {
            http_get {
              path = "/v2/health/live"
              port = 8000
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
          }
          resources {
            limits = {
              memory = "4Gi"
              cpu    = "2"
            }
            requests = {
              memory = "2Gi"
              cpu    = "1"
            }
          }

        }

        image_pull_secrets {
          name = "regcred"
        }
      }
    }
  }
}


resource "kubernetes_service" "triton" {
  metadata {
    name = "triton-server"
    annotations = {
      "service.beta.kubernetes.io/aws-load-balancer-type"                              = "nlb"
      "service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled" = "true"
      "service.beta.kubernetes.io/aws-load-balancer-connection-idle-timeout"           = "3600"
      "service.beta.kubernetes.io/aws-load-balancer-security-groups"                   = aws_security_group.triton_server.id
    }
  }
  spec {
    selector = {
      app = "triton-server"
    }
    port {
      name        = "http"
      port        = 8000
      target_port = 8000
      protocol    = "TCP"
    }
    port {
      name        = "grpc"
      port        = 8001
      target_port = 8001
      protocol    = "TCP"
    }
    port {
      name        = "metrics"
      port        = 8002
      target_port = 8002
      protocol    = "TCP"
    }
    port {
      name        = "websocket"
      port        = 8080
      target_port = 8080
      protocol    = "TCP"
    }
    type = "LoadBalancer"
  }
}





#resource "kubernetes_service" "triton" {
#  metadata {
#    name = "triton-server"
#  }
#  spec {
#    selector = {
#      app = "triton-server"
#    }
#    port {
#      name        = "http"
#      port        = 8000
#      target_port = 8000
#    }
#    port {
#      name        = "grpc"
#      port        = 8001
#      target_port = 8001
#    }
#    port {
#      name        = "metrics"
#      port        = 8002
#      target_port = 8002
#    }
#    type = "LoadBalancer"
#  }
#}
