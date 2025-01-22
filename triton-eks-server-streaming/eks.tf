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
    }
  }
}
