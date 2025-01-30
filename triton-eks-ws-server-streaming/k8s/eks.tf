## eks.tf
#module "eks" {
#  source  = "terraform-aws-modules/eks/aws"
#  version = "19.15.1"
#
#  cluster_name    = "triton-streaming-cluster"
#  cluster_version = "1.27"
#
#  vpc_id     = module.vpc.vpc_id
#  subnet_ids = module.vpc.private_subnets
#
#  cluster_endpoint_public_access = true
#
#  manage_aws_auth_configmap = true
#
#  aws_auth_users = [
#    {
#      userarn  = "arn:aws:iam::${var.account_id}:user/${var.username}"
#      username = "${var.username}"
#      groups   = ["system:masters"]
#    }
#  ]
#
#  eks_managed_node_groups = {
#    general = {
#      desired_size   = 1
#      min_size       = 1
#      max_size       = 1
#      instance_types = ["t3.xlarge"]
#      capacity_type  = "ON_DEMAND"
#
#      # Add SSM access
#      iam_role_additional_policies = {
#        AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
#      }
#
#      block_device_mappings = {
#        xvda = {
#          device_name = "/dev/xvda"
#          ebs = {
#            volume_size = 100
#            volume_type = "gp3"
#          }
#        }
#      }
#
#      labels = {
#        Environment = "development"
#      }
#
#      tags = {
#        Environment = "development"
#      }
#    }
#  }
#  resource "aws_security_group" "triton_server" {
#    name        = "triton-server-sg"
#    description = "Security group for Triton Server"
#    vpc_id      = module.vpc.vpc_id
#
#    ingress {
#      description = "WebSocket"
#      from_port   = 8080
#      to_port     = 8080
#      protocol    = "tcp"
#      cidr_blocks = ["0.0.0.0/0"]
#    }
#
#    ingress {
#      description = "HTTP"
#      from_port   = 8000
#      to_port     = 8000
#      protocol    = "tcp"
#      cidr_blocks = ["0.0.0.0/0"]
#    }
#
#    ingress {
#      description = "gRPC"
#      from_port   = 8001
#      to_port     = 8001
#      protocol    = "tcp"
#      cidr_blocks = ["0.0.0.0/0"]
#    }
#
#    ingress {
#      description = "Metrics"
#      from_port   = 8002
#      to_port     = 8002
#      protocol    = "tcp"
#      cidr_blocks = ["0.0.0.0/0"]
#    }
#
#    egress {
#      from_port   = 0
#      to_port     = 0
#      protocol    = "-1"
#      cidr_blocks = ["0.0.0.0/0"]
#    }
#
#    tags = {
#      Name = "triton-server-sg"
#    }
#  }
#}


# eks.tf
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.15.1"

  cluster_name    = "triton-streaming-cluster"
  cluster_version = "1.27"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  manage_aws_auth_configmap = true
  
  aws_auth_users = [
    {
      userarn  = "arn:aws:iam::${var.account_id}:user/${var.username}"
      username = "${var.username}"
      groups   = ["system:masters"]
    }
  ]

  eks_managed_node_groups = {
    general = {
      desired_size = 1
      min_size     = 1
      max_size     = 1
      instance_types = ["t3.xlarge"]
      capacity_type  = "ON_DEMAND"

      # Add SSM access
      iam_role_additional_policies = {
        AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
      }

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size = 100
            volume_type = "gp3"
          }
        }
      }

      labels = {
        Environment = "development"
      }

      tags = {
        Environment = "development"
      }

      vpc_security_group_ids = [aws_security_group.triton_server.id]
    }
  }
}
