# vpc.tf
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "triton-vpc"
  cidr = "192.168.0.0/20"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["192.168.0.0/24", "192.168.2.0/24"]
  public_subnets  = ["192.168.4.0/24", "192.168.6.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_vpn_gateway = false

  tags = {
    Environment = "development"
    Terraform   = "true"
  }
}
